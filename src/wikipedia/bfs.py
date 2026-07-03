from collections import deque

from src.schemas.entity import Entity
from src.wikipedia.filter import keep


class WikipediaBFS:

    def __init__(self, client):

        self.client = client

    def make_entity(self, link, parent):

        title = link["title"]

        if not keep(title):
            return None

        return Entity(
            title=title,
            url=self.client.get_url(title),
            depth=parent.depth + 1,
            parent=parent.title,
        )

    def discover(self, seed):

        visited = set()

        queue = deque()

        discovered = []

        queue.append(
            Entity(
                title=seed.title,
                url=self.client.get_url(seed.title),
                depth=0,
                parent=None,
            )
        )

        while queue:

            entity = queue.popleft()

            if entity.title in visited:

                continue

            visited.add(entity.title)

            discovered.append(entity)

            if entity.depth >= seed.max_depth:

                continue

            links = self.client.get_links(entity.title)

            for link in links:

                title = link["title"]

                if not keep(title):
                    continue

                if title in visited:
                    continue

                child = self.make_entity(link, entity)

                if child is None:
                    continue

                if child.title in visited:
                    continue

                entity.children.append(child.title)

                queue.append(child)

            if len(discovered) >= seed.entity_limit:

                break

        return discovered