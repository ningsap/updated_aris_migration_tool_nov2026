# Diagram Forge 

Diagram Forge is a Python package for optimizing the layout of BPMN diagrams. It is simple to use yet powerful enough to handle complex diagrams.

### Table of Contents <!-- omit in toc -->

- [Quick Start Guide](#quick-start-guide)
- [Collaboration Guide](#collaboration-guide)
  - [1. GitHub Issues](#1-github-issues)
  - [2. Pull Requests](#2-pull-requests)
  - [3. Custom non-generic or client/project specific changes](#3-custom-non-generic-or-clientproject-specific-changes)


### Detailed Documentations

- [Concept](docs/concept.md) - Explains the concept behind the package and how it works with links to deep dive information.
- [Usage](docs/usage.md) - How to use the package with the model representation instead of the SPM JSON.
- [Configuration](docs/configuration.md) - How to configure the package for your needs.
- [Testing](docs/testing.md) - How to test your changes before committing them.

## Quick Start Guide

This package is meant to be installed using the uv package manager. To install it, run the following command in your project:

```bash
uv add git+https://github.tools.sap/Signavio-Professional-Services/diagramforge.git
```

After successfully installing the package, you can use it in your Python code like this:

```python
from diagramforge.diagramforge import DiagramForge


diagram_forge = DiagramForge(my_diagram_model_representation or my_diagram_json)
optimized_diagram_json = diagram_forge.to_spm_json()
```

If all goes well, you should see the optimized diagram JSON in the `optimized_diagram_json` variable. It is basically the same as the input diagram JSON, but with the positions of the elements optimized. This could be uploaded to SPM directly.

For more information about how to use the model representation to build you own diagrams from scratch, see the [Usage](docs/usage.md) page.

For configuration options, see the [Configuration](docs/configuration.md) page.

## Collaboration Guide

Here you find the three major ways for collaboration in regards to this package. Please read through the following, if you want to implement new features or fix bugs to get a grasp of what to consider and which option suits your needs best. 

Generally, the `main` branch is protected and can only be updated through pull requests from the `dev` branch of this repository. The `dev` branch is the default branch for development and should be used as pull request target for other branches that contain fixes or features.

### 1. GitHub Issues

If you find a bug or have a feature request, please open an issue on GitHub. I will try to address it as soon as possible. If you want to work on the issue yourself, please mention that in the issue description. In case you don't mentioned that (see 2.), I am going to assume that you are just reporting the issue and I will take care of it.

When opening an issue, please provide as much information as possible. This includes a detailed description of the issue, the expected behavior, and the actual behavior. If you can, please also provide a minimal example that reproduces the issue. This helps to understand the problem and to fix it faster.

### 2. Pull Requests

In case you want to fix something or add a new feature, you are also welcome to do it on your own. For that matter, please keep the following in mind:

- ***Test your changes thoroughly!*** This package is used in production across multiple projects, so we need to make sure that it works as expected. Please follow the instructions at [Testing](docs/testing.md) to test your changes.

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
uv add git+https://github.tools.sap/<GitHub Space or User>/<Forked Repo Name>.git
```

If you want to contribute your changes back to the main repository, please open an issue or a pull request as described above.

This repo should not end up as the next graveyard of abandoned branches. So please, if you are not sure about your changes, open an issue first and discuss it with me. I am happy to help you with your changes and to guide you through the process.