# User-based Access Control with Agent Files for LangChain in Python

An example Python app demonstrating how to integrate Pangea's [AuthZ][] and
[Vault][] service into a LangChain app to apply user-based authorization to
control access to files fetched via agents.

## Prerequisites

- Python v3.12 or greater.
- pip v24.2 or [uv][] v0.4.24.
- A [Pangea account][Pangea signup] with AuthZ and Vault enabled.
- An [OpenAI API key][OpenAI API keys].
- A Google Drive folder containing documents. Note down the ID of the folder
  (see [the LangChain docs][retrieve-the-google-docs] for a guide on how to get
  the ID from the URL).
- A Google Cloud project with the [Google Drive API][] enabled.
- A Google service account with the `"https://www.googleapis.com/auth/drive.readonly"`
  scope.

The Google service account's credentials will also need to be added to Vault.
This would look like:

![New Secret prompt in Vault](./.github/assets/vault-new-secret.png)

Save the ID of the new Vault item for later.

## Setup

### Pangea AuthZ

The setup in AuthZ should look something like this:

#### Resource types

| Name        | Permissions |
| ----------- | ----------- |
| engineering | read        |
| finance     | read        |

#### Roles & access

> [!TIP]
> At this point you need to create 2 new Roles under the `Roles & Access` tab in the Pangea console named `engineering` and `finance`.

##### Role: engineering

| Resource type | Permissions (read) |
| ------------- | ------------------ |
| engineering   | ✔️                 |
| finance       | ❌                 |

##### Role: finance

| Resource type | Permissions (read) |
| ------------- | ------------------ |
| engineering   | ❌                 |
| finance       | ✔️                 |

#### Assigned roles & relations

| Subject type | Subject ID | Role/Relation |
| ------------ | ---------- | ------------- |
| user         | alice      | engineering   |
| user         | bob        | finance       |

### Repository

```shell
git clone https://github.com/pangeacyber/langchain-python-file-authz.git
cd langchain-python-file-authz
```

If using pip:

```shell
python -m venv .venv
source .venv/bin/activate
pip install .
```

Or, if using uv:

```shell
uv sync
source .venv/bin/activate
```

The sample can then be executed with:

```shell
python -m langchain_file_authz
```

## Usage

```
Usage: python -m langchain_file_authz [OPTIONS] PROMPT

Options:
  --user TEXT                    Unique username to simulate retrieval as.
                                 [required]
  --google-drive-folder-id TEXT  The ID of the Google Drive folder to fetch
                                 documents from.  [required]
  --vault-item-id TEXT           The item ID of the Google Drive credentials
                                 in Pangea Vault.  [required]
  --authz-token SECRET           Pangea AuthZ API token. May also be set via
                                 the `PANGEA_AUTHZ_TOKEN` environment
                                 variable.  [required]
  --vault-token SECRET           Pangea Vault API token. May also be set via
                                 the `PANGEA_VAULT_TOKEN` environment
                                 variable.  [required]
  --pangea-domain TEXT           Pangea API domain. May also be set via the
                                 `PANGEA_DOMAIN` environment variable.
                                 [default: aws.us.pangea.cloud; required]
  --model TEXT                   OpenAI model.  [default: gpt-4o-mini;
                                 required]
  --openai-api-key SECRET        OpenAI API key. May also be set via the
                                 `OPENAI_API_KEY` environment variable.
                                 [required]
  --help                         Show this message and exit.
```

For this example, we have various text documents from an Engineering department
and a Finance department in a Google Drive folder. Assuming user "alice" has
permission to see Engineering documents, they can query the LLM on information
regarding those documents:

```
python -m langchain_file_authz --google-drive-folder-id 1Kj77... --vault-item-id pvi_... "What document has the software architecture of the company?"
```

```
The software architecture of the company is detailed in the document titled "Internal Software Engineering," which outlines the internal systems and processes related to software development and HR management operations.
```

But they cannot query finance information:

```
python -m langchain_file_authz --google-drive-folder-id 1Kj77... --vault-item-id pvi_... "What is the top salary in the Engineering department?"
```

```
I am unable to determine the top salary in the Engineering department due to a lack of available documents in Google Drive.
```

[AuthZ]: https://pangea.cloud/docs/authz/
[Vault]: https://pangea.cloud/docs/vault/
[Pangea signup]: https://pangea.cloud/signup
[OpenAI API keys]: https://platform.openai.com/api-keys
[Google Drive API]: https://console.cloud.google.com/flows/enableapi?apiid=drive.googleapis.com
[uv]: https://docs.astral.sh/uv/
[retrieve-the-google-docs]: https://python.langchain.com/docs/integrations/retrievers/google_drive/#retrieve-the-google-docs
