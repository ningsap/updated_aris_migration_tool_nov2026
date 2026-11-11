*⚠️Note: This project is work in progress!⚠️*

# Installation

Please ensure to use this package always as a submodule.
It allows you to create your own branch, to provide adjustments which can be discussed in a weider audience or to add new features to this package.
To do so, you can clone this repo as a submodule in your project with:

```
git submodule add https://github.tools.sap/Signavio-Professional-Services/spm-client.git spmclient
```

__ONE TIME EXECUTION (Saved after first usage as submodule):__ It will ask for your Username and Password. Use your SAP I-Number with a big 'I' in the beginning and instead of your password you need to provide your personal developer token.
Please find instructions on how to create your token here:

```
https://sap-my.sharepoint.com/:v:/p/oliver_haselberger/EfQ6LOVpetBGiyn7MMoqqRcBNpAKRmLNnK0XLEnbbpmzlQ
```

This will allow you to alter the code inside this package while maintaining the correct version of your
project as well as this one.

*Note: A reopening of the IDE could be needed when using an integrated Git module*

# Usage

Usage as submodule:

```
from spmclient.spm.spmclient import SPMClient

spm = SPMClient('path/to/my/spmconfig.yaml')
```

The `spmconfig.yaml` is provided as a template within the submodule and looks like this:

```
mail: <your mail>
password: <your password>
workspace: <your workspace ID>
host: https://editor.signavio.com #<or app-us. / app-au.>
```

# IMPORTANT 
*⚠️ Create a new branch before pushing your changes! So we know what has changed and can review it. ⚠️*

Should you decide to add your custom features to this package, use that submodule
as a git repo. 
You also can pull new changes as you would with any other git repo or you can pull your main project with this additional parameter:

```
git pull --recurse-submodules
```

*NOTE: Most of the described actions can also performed within PyCharm or similar IDE's without using the terminal/console.*

