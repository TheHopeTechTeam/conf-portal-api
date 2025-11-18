"""
TemplateRenderProvider
"""
import os

from jinja2 import Environment, FileSystemLoader, Template


# pylint: disable=too-few-public-methods
class TemplateRenderProvider:
    """TemplateRenderProvider"""

    def __init__(self):
        pass

    @property
    def file_loader(self) -> Environment:
        """

        :return:
        """
        paths = self.__get_all_template_dir("./portal/templates")
        return Environment(
            loader=FileSystemLoader(searchpath=paths),
            enable_async=True
        )

    def __get_all_template_dir(self, scan_path: str) -> list:
        paths = [scan_path]
        for _dir in os.listdir(scan_path):
            search_path = f"{scan_path}/{_dir}"
            if not os.path.isdir(search_path):
                continue
            child_paths = self.__get_all_template_dir(search_path)
            paths.extend(child_paths)
        return paths

    @staticmethod
    async def __renderer(template: Template, **kwargs: dict) -> str:
        """

        :param template:
        :param kwargs:
        :return:
        """
        return await template.render_async(**kwargs)

    async def render_email_by_file(self, name: str, **kwargs) -> str:
        """

        :param name:
        :param kwargs:
        :return:
        """
        template = self.file_loader.get_template(name=name)
        return await self.__renderer(template=template, **kwargs)
