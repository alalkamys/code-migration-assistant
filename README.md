<!-- markdownlint-configure-file {
  "MD033": false,
  "MD041": false,
  "MD029": false
} -->

# Code Migration Assistant

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/alalkamys/code-migration-assistant)](https://github.com/alalkamys/code-migration-assistant/issues)
[![GitHub Release](https://img.shields.io/github/v/release/alalkamys/code-migration-assistant)](https://github.com/alalkamys/code-migration-assistant/releases/)

`Code Migration Assistant` is a powerful tool designed to streamline and automate the process of code migration at scale. With its intuitive interface and robust features, it enables users to effortlessly search for and replace patterns across multiple repositories, saving time and ensuring consistency in codebases.

With `Code Migration Assistant` teams can accelerate the migration of code repositories. By automating tedious tasks, ensuring uniformity across codebases, it empowers teams to execute seamless migrations with confidence and efficiency.

## Table of contents

<!--ts-->

- [Code Migration Assistant](#code-migration-assistant)
  - [Table of contents](#table-of-contents)
  - [Key Features](#key-features)
  - [Why Code Migration Assistant?](#why-code-migration-assistant)
  - [Requriements](#requriements)
  - [Getting Started](#getting-started)
  - [Creating Your Own Targets Config File](#creating-your-own-targets-config-file)
    - [`mode` (Optional)](#mode-optional)
    - [`targetRepos` (Required)](#targetrepos-required)
    - [`targetBranch` (Optional)](#targetbranch-optional)
    - [`commitMessage` (Optional)](#commitmessage-optional)
    - [`pullRequest` (Optional)](#pullrequest-optional)
    - [`replacements` (Optional)](#replacements-optional)
    - [`filesToExclude` (Optional)](#filestoexclude-optional)
  - [Environment Variables](#environment-variables)
  - [⚔️ Developed By](#️-developed-by)
  - [:book: Author](#book-author)

## Key Features

- **Efficiency**: Automates tedious tasks involved in code migration, reducing manual effort and time consumption.
- **Consistency**: Guarantees uniformity and standardization across multiple repositories by consistently applying replacements and enforcing standardized commit messages, branches, and pull request payloads.
- **Idempotency:** Regardless of how many times you run it, `Code Migration Assistant` always reaches the desired state, eliminating the risk of unintended side effects or inconsistencies.
- **Reduced Errors:** Minimizes the likelihood of human errors and ensures accuracy by executing migration tasks consistently according to predefined configurations.
- **Scalability:** Scales effortlessly to handle migrations across tens or hundreds of repositories, saving valuable time and resources for teams.
- **Flexibility**: Supports customization through configurable `exact`/`regex` patterns and replacements to suit various migration scenarios.
- **Versatility**: Compatible with different source control management providers like `GitHub`, `GitHub Enterprise` and `Azure DevOps`, offering flexibility in diverse development environments.

## Why Code Migration Assistant?

In large-scale software systems, even the slightest changes can necessitate multiple replacements across numerous repositories. Often, these changes involve modifying URLs, secret paths, variable names, or other patterns that are common across **tens**, or even **hundreds**, of solutions. Manually performing these replacements across multiple repositories is time-consuming, error-prone, and can lead to inconsistencies.

`Code Migration Assistant` addresses this challenge by automating the process of code migration at scale. By providing a centralized solution for managing and executing replacements across multiple repositories, it streamlines the code migration workflow, reduces manual effort, and ensures consistency and accuracy across the entire codebase. `Code Migration Assistant` not only automates and enforces the process of replacing patterns across repositories but also standardizes branching, commit messages, and pull requests. By doing this, it promotes best practices and enhances collaboration among team members. This ensures that code changes are well-documented, easily reviewable, and seamlessly integrated into the development workflow.

With `Code Migration Assistant`, developers and DevOps teams can efficiently manage code changes, implement updates, and ensure that all repositories are synchronized with the latest requirements or standards. Whether it's updating URLs, replacing sensitive information, or standardizing variable names, `Code Migration Assistant` simplifies the process and empowers teams to focus on higher-value tasks.

## Requriements

- [Git:][git] `Code Migration Assistant` relies on Git for cloning and interacting with repositories. Make sure Git is installed on your system and configured properly.
- Python 3.6 or higher.
- Access to Target Repositories: Ensure that you have appropriate access permissions to clone and modify the target repositories specified in the configuration file (`config.json`).
- Environment Variables: Set up the required environment variables such as `AZURE_DEVOPS_PAT`, `GITHUB_TOKEN` and `GITHUB_ENTERPRISE_TOKEN` with the appropriate access permissions to authenticate with the respective SCM providers and raise pull requests.

## Getting Started

1. Clone the `Code Migration Assistant` repository.

```bash
git clone https://github.com/alalkamys/code-migration-assistant.git
```

2. Install the required dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

3. Configure the `config.json` file with the desired patterns and replacements. See [Creating Your Own Targets Config File](#creating-your-own-targets-config-file)

4. Run `Code Migration Assistant`:

```bash
CODE_MIGRATION_ASSISTANT_TARGETS_CONFIG_FILE='<path/to/your/config-file>' python main.py
```

> :bulb: **Tip:** See [all supported environment variables](#environment-variables)

5. Review the generated logs and output to ensure successful execution.

<div align="center">

![Code Migration Assistant Logs Output 01][code-migration-assistant-logs-01]

![Code Migration Assistant Logs Output 02][code-migration-assistant-logs-02]

</div>

6. Check the pull requests.

<div align="center">

![Code Migration Assistant Pull Request 01][code-migration-assistant-pr-github-01]

![Code Migration Assistant Pull Request 02][code-migration-assistant-pr-github-02]

</div>

## Creating Your Own Targets Config File

The targets configuration file (`config.json`) is a crucial component of `Code Migration Assistant`. It allows you to define the repositories you want to perform code migration operations on.

The `config.json` file defines the targets and their respective configurations. Below is an example of a `config.json` file:

```json
{
  "mode": "prod",
  "targetRepos": [
    {
      "name": "test-repo",
      "source": "remote-repos/test-repo",
      "type": "Local",
      "scmProvider": {
        "type": "azuredevops",
        "baseUrl": "https://dev.azure.com/TestOrg/",
        "project": "Test"
      }
    },
    {
      "name": "test-repo-2",
      "source": "https://TestOrg@dev.azure.com/TestOrg/Test2/_git/test-repo-2",
      "type": "Remote",
      "scmProvider": {
        "type": "azuredevops",
        "baseUrl": "https://dev.azure.com/TestOrg/",
        "project": "Test2"
      }
    }
  ],
  "targetBranch": {
    "name": "feat/code-migration",
    "from": "main"
  },
  "commitMessage": {
    "title": "Feat: Code Migration",
    "description": [
      "This change is to prepare for our organization code migration",
      "#### What has changed?",
      "- [x] Replaced all repos matched files with the required replacements",
      "- [x] Code is ready for the organization required migration"
    ]
  },
  "pullRequest": {
    "azuredevops": {
      "title": "Feat: Code Migration",
      "description": [
        "This change is to prepare for our organization code migration",
        "#### What has changed?",
        "- [x] Replaced all repos matched files with the required replacements",
        "- [x] Code is ready for the organization required migration"
      ],
      "labels": [
        {
          "name": "Migration"
        },
        {
          "name": "Code Migration"
        },
        {
          "name": "Code Migration Assistant"
        }
      ],
      "workItemRefs": [
        {
          "id": "8646"
        }
      ]
    }
  },
  "replacements": {
    "https://github.mycompany.com/old-org": "https://github.com/new-org",
    "name: \\s*old-org/([^\\s]+)": "name: new-org/\\1",
    "type: \\s*githubenterprise": "type: github"
  },
  "filesToExclude": ["test-repo/azure-pipelines.yaml"]
}
```

Below is an explanation of each field in the configuration file:

### `mode` (Optional)

- **Description**: Specifies the mode of operation for `Code Migration Assistant`.
- **Values**: `"dev"` or `"prod"`.
- **Default**: `"prod"`.
- **Usage**: Use `"dev"` mode for development/testing, this is used when you want want to test your patterns and confirm your results. In this mode `Code Migration Assistant` will only clone your repository and will not create a new branch nor will it modify your files. `"prod"` mode for production use. Using this mode, `Code Migration Assistant` will be fully functional; it will create a new branch, replace the matched patterns files with their replacements, will push the changes and raise a pull request.

> :memo: **Note:** You can choose not to raise a pull request by not adding `pullRequest` field in your configuration file. This is useful when you want to test things out on your feature branch before raising a pull request. When you are done you can add the `pullRequest` data and run `Code Migration Assistant` again, thanks to `Code Migration Assistant` idempotency it will reach the desired state by raising only the pull request.

### `targetRepos` (Required)

- **Description**: Specifies the list of target repositories along with their configurations.
- **Format**: Array of objects.
- **Fields**:
  - `name` (required): Name of the target repository.
  - `type` (required): Type of the repository (`Remote` or `Local`).
  - `source` (required): Source URL or local path of the repository.
  - `scmProvider` (required): Information about the source control management provider.
    - `type` (required): The type of SCM provider. Valid values are `"azuredevops"` and `"github"`.
    - Additional provider-specific fields:
      - For Azure DevOps:
        - `baseUrl` (required): The base URL of the Azure DevOps organization.
        - `project` (required): The name of the project in Azure DevOps.
      - For GitHub and GitHub Enterprise:
        - `domain` (required): The domain of the GitHub instance (e.g., `"github.com"`).
        - `ownerOrOrg` (required): The owner or organization of the GitHub repository.

### `targetBranch` (Optional)

- **Description**: Specifies the target branch on which the replacements will occur and will be the source branch for your pull requests.
- **Fields**:
  - `name` (required): Name of the target branch.
  - `from` (Optional): Source branch from which the target branch is created.

### `commitMessage` (Optional)

- **Description**: Specifies the commit message details for the pull request.
- **Fields**:
  - `title` (required): Title of the commit message.
  - `description` (optional): Description of the commit message (array of strings).

### `pullRequest` (Optional)

- **Description**: Specifies pull request details for each SCM provider.
- **Fields**: Object with keys as SCM provider names (`azuredevops` or `github`):

  - For `azuredevops`:

    - `targetRefName` (optional): The name of the target branch of the pull request. (e.g `main` or `refs/heads/main`). Defaults to the remote repository default branch.
    - `title` (required): The title of the pull request.
    - `description` (optional): The description of the pull request.
    - `labels` (optional): Labels to be applied to the pull request.
    - `workItemRefs` (optional): Work item references associated with the pull request.

    <br/>

    > :bulb: **Tip:** See [Azure DevOps Pull Requests - Create REST API][ado-api-create-pr]

  - For `github`:

    - `base` (optional): The name of the branch you want the changes pulled into. This should be an existing branch on the current repository. You cannot submit a pull request to one repository that requests a merge to a base of another repository (e.g `main` or `refs/heads/main`). Defaults to the remote repository default branch.
    - `title` (required): The title of the pull request.
    - `body` (optional): The body content of the pull request.
    - `maintainer_can_modify` (optional): Indicates whether maintainers can modify the pull request.

    <br/>

    > :bulb: **Tip:** See [GitHub Create a pull requests API][github-api-create-pr]

> :warning: **Warning:** The `pullRequest` field must match the `scmProvider.type` specified in the `targetRepos[]`

### `replacements` (Optional)

- **Description**: Specifies patterns to be replaced in the codebase.
- **Format**: Object with pattern-replacement pairs.
- **Example**:

```json
"replacements": {
    "https://github.mycompany.com/old-org": "https://github.com/new-org",
    "name: \\s*old-org/([^\\s]+)": "name: new-org/\\1",
    "type: \\s*githubenterprise": "type: github",
    "endpoint: \\s*github-enterprise": "endpoint: github",
    "terraform-aws-modules/": "https://github.com/terraform-aws-modules.git//",
    "old-url": "new-url",
    "old_variable_name": "new_variable_name"
}
```

> :memo: **Note:** `replacements` field follows the [Python re module's syntax for regular expressions][python-re-module]. Ensure that the patterns provided match the intended strings in the codebase for successful replacements.

### `filesToExclude` (Optional)

- **Description**: Specifies files or paths to be excluded from processing during code migration.
- **Format**: Array of file or directory paths relative to the repository root.
- Follows the format `<repository_name>/<path/to/file>`

## Environment Variables

| Environment Variable                                   | Usage                                                                     | Default Value                              |
| ------------------------------------------------------ | ------------------------------------------------------------------------- | ------------------------------------------ |
| `CODE_MIGRATION_ASSISTANT_APP_NAME`                    | Name of the Code Migration Assistant application                          | `code_migration_assistant`                 |
| `CODE_MIGRATION_ASSISTANT_LOG_LEVEL`                   | Log level for the Code Migration Assistant application                    | `INFO`                                     |
| `CODE_MIGRATION_ASSISTANT_TARGETS_CONFIG_FILE`         | Path to the targets configuration file for Code Migration Assistant       | `./config.json`                            |
| `CODE_MIGRATION_ASSISTANT_REMOTE_TARGETS_CLONING_PATH` | Path where remote repositories will be cloned by Code Migration Assistant | `./remote-targets`                         |
| `AZURE_DEVOPS_PAT`                                     | Azure DevOps Personal Access Token (PAT)                                  | `None`                                     |
| `GITHUB_TOKEN`                                         | GitHub Personal Access Token (PAT)                                        | `None`                                     |
| `GITHUB_ENTERPRISE_TOKEN`                              | GitHub Enterprise Personal Access Token (PAT)                             | `None`                                     |
| `CODE_MIGRATION_ASSISTANT_USER_AGENT`                  | User agent used for HTTP requests by Code Migration Assistant             | `alalkamys/code-migration-assistant`       |
| `CODE_MIGRATION_ASSISTANT_ACTOR_USERNAME`              | Actor username used for git identity setup                                | `Code Migration Assistant Agent`           |
| `CODE_MIGRATION_ASSISTANT_ACTOR_EMAIL`                 | Actor email used for git identity setup                                   | `code_migration_assistant_agent@gmail.com` |

<br />

## ⚔️ Developed By

<a href="https://www.linkedin.com/in/shehab-el-deen/" target="_blank"><img alt="LinkedIn" align="right" title="LinkedIn" height="24" width="24" src="docs/assets/imgs/linkedin.png"></a>

Shehab El-Deen Alalkamy

<br />

## :book: Author

Shehab El-Deen Alalkamy

<!--*********************  R E F E R E N C E S  *********************-->

<!-- * Links * -->

[git]: https://git-scm.com/
[ado-api-create-pr]: https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-requests/create?view=azure-devops-rest-7.1&tabs=HTTP
[github-api-create-pr]: https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#create-a-pull-request
[python-re-module]: https://docs.python.org/3/library/re.html

<!-- * Images * -->

[code-migration-assistant-logs-01]: docs/assets/imgs/code-migration-assistant-logs-01.png
[code-migration-assistant-logs-02]: docs/assets/imgs/code-migration-assistant-logs-02.png
[code-migration-assistant-pr-github-01]: docs/assets/imgs/code-migration-assistant-pr-github-01.png
[code-migration-assistant-pr-github-02]: docs/assets/imgs/code-migration-assistant-pr-github-02.png
