""" inventaire data connector """
from .abstract_connector import AbstractConnector, SearchResult, Mapping
from .abstract_connector import get_data
from .connector_manager import ConnectorException


class Connector(AbstractConnector):
    """ instantiate a connector for OL """

    def __init__(self, identifier):
        super().__init__(identifier)

        get_first = lambda a: a[0]
        shared_mappings = [
            Mapping("id", remote_field="uri", formatter=self.get_remote_id),
            Mapping("bnfId", remote_field="wdt:P268", formatter=get_first),
            Mapping("openlibraryKey", remote_field="wdt:P648", formatter=get_first),
        ]
        self.book_mappings = [
            Mapping("title", remote_field="wdt:P1476", formatter=get_first),
            Mapping("subtitle", remote_field="wdt:P1680", formatter=get_first),
            Mapping("inventaireId", remote_field="uri"),
            Mapping("cover", remote_field="image", formatter=self.get_cover_url),
            Mapping("isbn13", remote_field="wdt:P212", formatter=get_first),
            Mapping("isbn10", remote_field="wdt:P957", formatter=get_first),
            Mapping("oclcNumber", remote_field="wdt:P5331", formatter=get_first),
            Mapping("goodreadsKey", remote_field="wdt:P2969", formatter=get_first),
            Mapping("librarythingKey", remote_field="wdt:P1085", formatter=get_first),
            Mapping("languages", remote_field="wdt:P407", formatter=self.resolve_keys),
            Mapping("publishers", remote_field="wdt:P123", formatter=self.resolve_keys),
            Mapping("publishedDate", remote_field="wdt:P577", formatter=get_first),
            Mapping("pages", remote_field="wdt:P1104", formatter=get_first),
            Mapping(
                "subjectPlaces", remote_field="wdt:P840", formatter=self.resolve_keys
            ),
            Mapping("subjects", remote_field="wdt:P921", formatter=self.resolve_keys),
            Mapping("asin", remote_field="wdt:P5749", formatter=get_first),
        ] + shared_mappings
        # TODO: P136: genre, P674 characters, P950 bne

        self.author_mappings = [
            Mapping("id", remote_field="uri", formatter=self.get_remote_id),
            Mapping("name", remote_field="labels", formatter=get_language_code),
            Mapping("goodreadsKey", remote_field="wdt:P2963", formatter=get_first),
            Mapping("isni", remote_field="wdt:P213", formatter=get_first),
            Mapping("viafId", remote_field="wdt:P214", formatter=get_first),
            Mapping("gutenberg_id", remote_field="wdt:P1938", formatter=get_first),
            Mapping("born", remote_field="wdt:P569", formatter=get_first),
            Mapping("died", remote_field="wdt:P570", formatter=get_first),
        ] + shared_mappings

    def get_remote_id(self, value):
        """ convert an id/uri into a url """
        return "{:s}?action=by-uris&uris={:s}".format(self.books_url, value)

    def get_book_data(self, remote_id):
        data = get_data(remote_id)
        extracted = list(data.get("entities").values())
        try:
            data = extracted[0]
        except KeyError:
            raise ConnectorException("Invalid book data")
        # flatten the data so that images, uri, and claims are on the same level
        return {
            **data.get("claims"),
            **{k: data.get(k) for k in ["uri", "image", "labels"]},
        }

    def parse_search_data(self, data):
        return data.get("results")

    def format_search_result(self, search_result):
        images = search_result.get("image")
        cover = (
            "{:s}/img/entities/{:s}".format(self.covers_url, images[0])
            if images
            else None
        )
        return SearchResult(
            title=search_result.get("label"),
            key="{:s}?action=by-uris&uris={:s}".format(
                self.books_url, search_result.get("uri")
            ),
            view_link="{:s}{:s}".format(self.base_url, search_result.get("uri")),
            cover=cover,
            connector=self,
        )

    def parse_isbn_search_data(self, data):
        """ boop doop """

    def format_isbn_search_result(self, search_result):
        """ beep bloop """

    def is_work_data(self, data):
        return data.get("type") == "work"

    def get_edition_from_work_data(self, data):
        value = data.get("uri")
        url = "{:s}?action=reverse-claims&property=P629&value={:s}".format(
            self.books_url, value
        )
        data = get_data(url)
        try:
            uri = data["uris"][0]
        except KeyError:
            raise ConnectorException("Invalid book data")
        return self.get_book_data(self.get_remote_id(uri))

    def get_work_from_edition_data(self, data):
        try:
            uri = data["claims"]["wdt:P629"]
        except KeyError:
            raise ConnectorException("Invalid book data")
        return self.get_book_data(self.get_remote_id(uri))

    def get_authors_from_data(self, data):
        authors = data.get("wdt:P50")
        for author in authors:
            yield self.get_or_create_author(self.get_remote_id(author))

    def expand_book_data(self, book):
        return

    def get_cover_url(self, cover_blob, *_):
        """format the relative cover url into an absolute one:
        {"url": "/img/entities/e794783f01b9d4f897a1ea9820b96e00d346994f"}
        """
        cover_id = cover_blob[0].get("url")
        if not cover_id:
            return None
        return "%s%s" % (self.covers_url, cover_id)

    def resolve_keys(self, keys):
        """ cool, it's "wd:Q3156592" now what the heck does that mean """
        results = []
        for uri in keys:
            try:
                data = self.get_book_data(self.get_remote_id(uri))
            except ConnectorException:
                continue
            results.append(get_language_code(data.get("labels")))
        return results


def get_language_code(options, code="en"):
    """ when there are a bunch of translation but we need a single field """
    return options.get(code)
