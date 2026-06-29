from apispec.core import APISpec


class TornOpenAPISpec(APISpec):
    def __init__(self, title, version, openapi_version, plugins=(), **options):
        super().__init__(title, version, openapi_version, plugins, **options)
        self.__tags = set()
        self.handler_tags = []

    def tag(self, tag, tag_type=None):
        if tag["name"] not in self.__tags:
            self.__tags.add(tag["name"])
            if tag_type == "handler":
                self.handler_tags.append(tag["name"])
            super().tag(tag)
