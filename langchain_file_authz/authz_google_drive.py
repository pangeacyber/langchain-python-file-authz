from __future__ import annotations

import logging

from langchain_googledrive.utilities.google_drive import (  # type: ignore[import-untyped]
    GoogleDriveAPIWrapper,
    GoogleDriveUtilities,
)
from pangea import PangeaConfig
from pangea.services import AuthZ
from pangea.services.authz import Resource, Subject
from pydantic import SecretStr

logger = logging.getLogger(__name__)


class PangeaAuthZGoogleDriveAPIWrapper(GoogleDriveAPIWrapper):
    """Google Drive search with Pangea AuthZ user-based access control."""

    _client: AuthZ

    def __init__(self, *, username: str, token: SecretStr, domain: str = "aws.us.pangea.cloud", **kwargs) -> None:
        super().__init__(**kwargs)

        self._client = AuthZ(token=token.get_secret_value(), config=PangeaConfig(domain=domain))
        self._subject = Subject(type="user", id=username)

    def run(self, query: str) -> str:
        snippets = []
        logger.debug(f"{query=}")
        for document in self.lazy_get_relevant_documents(query=query, num_results=self.num_results):
            # Fetch parent folder.
            file = self._get_file_by_id(document.metadata["id"])
            parent_id = next(iter(file.get("parents", [])), None)
            if parent_id:
                parent_folder = self._get_file_by_id(parent_id, fields="id, name")
                parent_folder_name = parent_folder.get("name")

                # Check if user is authorized to read from the parent folder.
                response = self._client.check(
                    resource=Resource(type=parent_folder_name), action="read", subject=self._subject
                )

                # Do not include the document if the user does not have access
                # to its parent folder.
                if response.result is None or not response.result.allowed:
                    logger.info(
                        f"User {self._subject.id} is not authorized to read from {parent_folder_name} ({parent_id}), "
                        f"and thus cannot access document {document.metadata['name']}."
                    )
                    continue

            content = document.page_content

            if (
                self.mode in ["snippets", "snippets-markdown"]
                and "summary" in document.metadata
                and document.metadata["summary"]
            ):
                content = document.metadata["summary"]

            if self.mode == "snippets":
                snippets.append(
                    f"Name: {document.metadata['name']}\n"
                    f"Source: {document.metadata['source']}\n" + f"Summary: {content}"
                )
            elif self.mode == "snippets-markdown":
                snippets.append(
                    f"[{document.metadata['name']}]" f"({document.metadata['source']})<br/>\n" + f"{content}"
                )
            elif self.mode == "documents":
                snippets.append(
                    f"Name: {document.metadata['name']}\n"
                    f"Source: {document.metadata['source']}\n" + f"Summary: "
                    f"{GoogleDriveUtilities._snippet_from_page_content(content)}"
                )
            elif self.mode == "documents-markdown":
                snippets.append(
                    f"[{document.metadata['name']}]"
                    f"({document.metadata['source']})<br/>"
                    + f"{GoogleDriveUtilities._snippet_from_page_content(content)}"
                )
            else:
                raise ValueError(f"Invalid mode `{self.mode}`")

        if not len(snippets):
            return "No document found"

        return "\n\n".join(snippets)
