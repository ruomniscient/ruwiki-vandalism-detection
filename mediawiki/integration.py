import dateutil.parser
import itertools
from injector import inject
from typing import Iterator
from .api import MediaWikiApi
from models import Instance, Revision, Page, RegisteredUser, Guest


class MediaWikiObjectConversion:

    @staticmethod
    def convert_revision(raw: dict) -> Revision:
        if "anon" in raw:
            user = Guest(str(raw["user"]))
        else:
            user = RegisteredUser(int(raw["userid"]), str(raw["user"]))

        return Revision(rev_id=int(raw["revid"]),
                        user=user,
                        timestamp=dateutil.parser.parse(raw["timestamp"]),
                        comment=str(raw["comment"]),
                        is_minor=("minor" in raw)) 

    @staticmethod
    def convert_page(raw: dict) -> Page:
        page = Page(page_id=int(raw["pageid"]),
                    title=str(raw["title"]),
                    ns=int(raw["ns"]))
                    
        return page

class BadRevisionIdException(Exception):
    pass

class MediaWikiIntegration:
    REVISION_PROPERTIES = ['ids', 'timestamp', 'user', 'userid', 'comment', 'flags']

    @inject
    def __init__(self, api: MediaWikiApi):
        self.api = api

    def load_group_members(self, group_name: str) -> Iterator[RegisteredUser]:
        for raw in self.api.query_users_for_group(group_name):
            yield RegisteredUser(
                user_id=int(raw["userid"]),
                user_name=str(raw["name"]))
        
    def load_single_revision_instance(self, rev_id: int) -> Instance:
        response = list(self.api.query_revisions_by_ids([rev_id], self.REVISION_PROPERTIES))
        if len(response) == 0:
            raise BadRevisionIdException()

        page_raw = response[0]
        page = MediaWikiObjectConversion.convert_page(page_raw)

        instance = Instance(page, rev_id)
        instance.revisions.replace([
            MediaWikiObjectConversion.convert_revision(page_raw["revisions"][0])
        ])

        return instance

    def load_revisions_into_instance(self, instance: Instance, count: int):
        response = self.api.query_revisions_for_page(
            page_id=instance.page.page_id,
            rvprop=self.REVISION_PROPERTIES,
            revs_limit=count)

        response_list = list(itertools.islice(response, count))
        instance.revisions.replace([
            MediaWikiObjectConversion.convert_revision(x) for x in response_list
        ])
        
