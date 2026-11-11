# ARIS_Migration_Tool

Setup
------

```bash
git add https://github.tools.sap/Signavio-Professional-Services/diagramforge.git
git add submodule https://github.tools.sap/Signavio-Professional-Services/vc_model_builder.git

git submodule update --init --recursive 
```

Features 
------

1. Regarding positioning of bpmn elements :
   - Events and gateways do not have any responsible information in the data. 
     The predecessors and successors of these shapes are fetched recursively until there is a task or collapsed subprocess with a lane. 
     Then these events and gateways are positioned into the same lane.
2. For positioing of VC elements, please check the vc model builder module. 
3. Tool supports FAD, Matrix Models, Data Models
4. Attribute handling:
   - Supports text, drop downs, dictionary items, urls ( please check respective configs)
   - Text attributes of models, shapes, dictionary items can be changed to Dictionary Items
   - Email can be extracted from an attribute, and a specific dictionary item can be created based on the email address.


Configuration:
------

For configuring the migration tool, please check the EXAMPLE_CONFIG.yaml under PROJECT_CONFIG folder.


# updated_aris_migration_tool_nov2026
