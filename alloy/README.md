# Alloy

A consolidated collection of various utility tools for Python in one place. This is the new implementation of the `pyutils` package, now using the poetry package manager.

### Table of Contents <!-- omit in toc -->
- [Quick Start Guide](#quick-start-guide)
- [Overview](#overview)
  - [Configuration options](#configuration-options)
  - [General utilities](#general-utilities)
  - [File handling](#file-handling)
  - [Logger](#logger)
  - [Database utility](#database-utility)
  - [Task Watch](#task-watch)
- [Collaboration Guide](#collaboration-guide)
  - [1. GitHub Issues](#1-github-issues)
  - [2. Pull Requests](#2-pull-requests)
  - [3. Custom non-generic or client/project specific changes](#3-custom-non-generic-or-clientproject-specific-changes)


## Quick Start Guide

This package is meant to be installed using the poetry package manager. To install it, run the following command in your project:

```bash
poetry add git+https://github.tools.sap/Signavio-Professional-Services/alloy.git#stable-latest
```

That's it! You can now import the package in your project and use the various utility functions provided by the package. Here's an example:

```python
from alloy.databases.database_utility_factory import DatabaseUtilityFactory

dbu = DatabaseUtilityFactory.get_database_utility(db_engine="sqlite", db_name="MySQLiteDB")
```

See the list of utility functions and classes below.

## Overview

Here is a quick overview of all modules that this package contains. Click the headings to get more information about each module.

### [Configuration options](docs/configuration.md)

Please see the linked documentation for info about the configuration options. 

> This approach will be updated soon to allow for more flexible configuration options during runtime.

### [General utilities](/alloy/general/helpers.py)

A collection of general utility functions and classes that can be used in various projects. Please see the linked in-code documentation for more information. For now, it just contains the `helpers.py` file, which contains a few utility functions.

### [File handling](/alloy/file_handler/)

Various modules for reading and writing files. This includes:

- [JSON](/alloy/file_handler/json_files.py)
- [CSV](/alloy/file_handler/csv_files.py)
- [YAML](/alloy/file_handler/yaml_files.py)

### [Logger](docs/logger_factory.md)

The logger factory provides a simple way to create a logger object that can be used to log messages to the console or a file. This approach is based on the [loguru](https://github.com/Delgan/loguru) package, which is a more user-friendly and powerful logging package than the built-in logging module.

### [Database utility](/docs/database_utility.md)

The database utility provides a simple way to interact with databases. It is based on the [SQLAlchemy](https://www.sqlalchemy.org/) package, which is a powerful and flexible SQL toolkit and Object-Relational Mapping (ORM) library for Python. The database utility provides a simple way to create, read, update, and delete records in a database.

### [Task Watch](/docs/task_watch.md)

A combined approach that was previously named `FileTaskTracker` and `TaskTracker`. The `task_watch` module provides a way to monitor the progress of a task. It is useful for long-running tasks that you want to keep track of, such as heavy calculations, data processing or network requests. An example use case could be the upload of diagrams during a migration where could check whether a specific diagram has been uploaded or not.

## Collaboration Guide

Here you find the three major ways for collaboration in regards to this package. Please read through the following, if you want to implement new features or fix bugs to get a grasp of what to consider and which option suits your needs best. 

Generally, the `main` branch is protected and can only be updated through pull requests from the `dev` branch of this repository. The `dev` branch is the default branch for development and should be used as pull request target for other branches that contain fixes or features.

### 1. GitHub Issues

If you find a bug or have a feature request, please open an issue on GitHub. I will try to address it as soon as possible. If you want to work on the issue yourself, please mention that in the issue description. In case you don't mentioned that (see 2.), I am going to assume that you are just reporting the issue and I will take care of it.

When opening an issue, please provide as much information as possible. This includes a detailed description of the issue, the expected behavior, and the actual behavior. If you can, please also provide a minimal example that reproduces the issue. This helps to understand the problem and to fix it faster.

### 2. Pull Requests

In case you want to fix something or add a new feature, you are also welcome to do it on your own. For that matter, please keep the following in mind:

- ***Test your changes thoroughly!*** This package is used in production across multiple projects, so we need to make sure that it works as expected.

- Document your changes. If you add new features or change existing ones, please update the documentation accordingly, in code as well as here. You can find the documentation in the `docs` folder.

- Make sure that your changes are compatible with the existing codebase. If you are not sure, please open an issue first and discuss your changes with me.

- Please use best practices when writing code. This includes following the PEP8 style guide, sorting of (only used) imports, writing clean and readable code, and using meaningful variable and function names. 

> ⚠️ ***IMPORTANT*** ⚠️ Please avoid unnecessary or lazy shortcuts and workarounds! This codebase should stay as clean, maintainable and efficient as possible. Hence, I will also ask for a better solution if I notice something like that.


- When committing your changes, please use atomic commits and write meaningful commit messages. This helps to understand what has been changed and why. To get an idea, see this article: [10 Essential Practices for Better Git Commits and Why They Matter](https://medium.com/@saeid/10-essential-practices-for-better-git-commits-and-why-they-matter-3cfc420bf53e).

With that in mind, you can start working on your changes. When you are done, please open a pull request on GitHub. Ideally, you would also link the related issue in the pull request description.

### 3. Custom non-generic or client/project specific changes

If you need to implement a feature or fix a bug that is specific to your project or client, please ***FORK*** this repository instead of just creating a new branch and make the changes there. This way, you can keep your changes separate from the main repository and still benefit from the updates and improvements that are made here.

Feel free to name the fork as you like, but you will have to adjust the installation command in your project accordingly.

```bash
poetry add git+https://github.tools.sap/<GitHub Space or User>/<Forked Repo Name>.git
```