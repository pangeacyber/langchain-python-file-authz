from __future__ import annotations

import json
from typing import Any, override

import click
from dotenv import load_dotenv
from google.auth.credentials import TokenState
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_googledrive.tools.google_drive.tool import GoogleDriveSearchTool  # type: ignore[import-untyped]
from langchain_openai import ChatOpenAI
from pangea import PangeaConfig
from pangea.services import Vault
from pangea.services.vault.models.common import ItemType
from pydantic import SecretStr

from langchain_file_authz.authz_google_drive import PangeaAuthZGoogleDriveAPIWrapper

load_dotenv(override=True)


PROMPT = PromptTemplate.from_template(
    """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
)


class SecretStrParamType(click.ParamType):
    name = "secret"

    @override
    def convert(self, value: Any, param: click.Parameter | None = None, ctx: click.Context | None = None) -> SecretStr:
        if isinstance(value, SecretStr):
            return value

        return SecretStr(value)


SECRET_STR = SecretStrParamType()


@click.command()
@click.option("--user", required=True, help="Unique username to simulate retrieval as.")
@click.option(
    "--google-drive-folder-id",
    type=str,
    required=True,
    help="The ID of the Google Drive folder to fetch documents from.",
)
@click.option(
    "--vault-item-id",
    type=str,
    required=True,
    help="The item ID of the Google Drive credentials in Pangea Vault.",
)
@click.option(
    "--authz-token",
    envvar="PANGEA_AUTHZ_TOKEN",
    type=SECRET_STR,
    required=True,
    help="Pangea AuthZ API token. May also be set via the `PANGEA_AUTHZ_TOKEN` environment variable.",
)
@click.option(
    "--vault-token",
    envvar="PANGEA_VAULT_TOKEN",
    type=SECRET_STR,
    required=True,
    help="Pangea Vault API token. May also be set via the `PANGEA_VAULT_TOKEN` environment variable.",
)
@click.option(
    "--pangea-domain",
    envvar="PANGEA_DOMAIN",
    default="aws.us.pangea.cloud",
    show_default=True,
    required=True,
    help="Pangea API domain. May also be set via the `PANGEA_DOMAIN` environment variable.",
)
@click.option("--model", default="gpt-4o-mini", show_default=True, required=True, help="OpenAI model.")
@click.option(
    "--openai-api-key",
    envvar="OPENAI_API_KEY",
    type=SECRET_STR,
    required=True,
    help="OpenAI API key. May also be set via the `OPENAI_API_KEY` environment variable.",
)
@click.argument("prompt")
def main(
    *,
    prompt: str,
    user: str,
    google_drive_folder_id: str,
    vault_item_id: str,
    authz_token: SecretStr,
    vault_token: SecretStr,
    pangea_domain: str,
    model: str,
    openai_api_key: SecretStr,
) -> None:
    # Fetch service account credentials from Pangea Vault.
    vault = Vault(token=vault_token.get_secret_value(), config=PangeaConfig(domain=pangea_domain))
    vault_result = vault.get_bulk({"id": vault_item_id}, size=1).result
    assert vault_result
    assert vault_result.items[0].type == ItemType.SECRET
    raw_gdrive_cred = vault_result.items[0].item_versions[-1].secret
    assert raw_gdrive_cred

    # Authenticate with Google Drive.
    parsed_gdrive_cred = service_account.Credentials.from_service_account_info(
        json.loads(raw_gdrive_cred), scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    parsed_gdrive_cred.refresh(Request())
    assert parsed_gdrive_cred.token_state == TokenState.FRESH

    # Set up Pangea AuthZ + Google Drive tool.
    google_drive = GoogleDriveSearchTool(
        api_wrapper=PangeaAuthZGoogleDriveAPIWrapper(
            username=user,
            token=authz_token,
            domain=pangea_domain,
            credentials=parsed_gdrive_cred,
            folder_id=google_drive_folder_id,
            mode="documents-markdown",
            num_results=-1,
            recursive=True,
            template="gdrive-query-in-folder",
        )
    )
    tools = [google_drive]
    llm = ChatOpenAI(model=model, api_key=openai_api_key, temperature=0)
    agent = create_react_agent(tools=tools, llm=llm, prompt=PROMPT)
    agent_executor = AgentExecutor(agent=agent, tools=tools)

    click.echo(agent_executor.invoke({"input": prompt})["output"])


if __name__ == "__main__":
    main()
