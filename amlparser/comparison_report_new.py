import datetime

from openpyxl import Workbook

from amlparser.amlquery import AMLQuery
from amlparser.excel import Excel
import yaml

# =============================================================================
# Config
# =============================================================================

amlquery = AMLQuery('input/ARISAMLExportExample.xml')

with open('PROJECT_CONFIG/TEST_projectconfig.yaml', 'r') as file:
    config = yaml.safe_load(file)



model_types = list(config['diagram_mapping'].keys()) # ["MT_ENTERPRISE_BPMN_COLLABORATION", "MT_ENTERPRISE_BPMN_PROCESS", "MT_VAL_ADD_CHN_DGM", "MT_BPMN_COLLABORATION_DIAGRAM"]


# =============================================================================
# Shape Mapping
# =============================================================================

func_symbol_type_to_name = {}
'''
func_symbol_type_to_name.update(config['shape_mapping'])
func_symbol_type_to_name.update(config['object_mapping'])
func_symbol_type_to_name.update(config['aris_signavio_attribute_name_mapping'])
func_symbol_type_to_name.update(config['aris_signavio_shape_level_attribute_value_mapping'])
func_symbol_type_to_name.update(config['attribute_mapping_based_on_connection_type'])



'''
func_symbol_types =  list(func_symbol_type_to_name.keys())




# =============================================================================
# Helper Functions
# =============================================================================

def get_titles_links(item, c_item):
    urls = []
    for i in range(len(c_item["titleProperty"])):
        titleProp = c_item["titleProperty"][i]
        linkProp = c_item["linkProperty"][i]
        title = ""
        link = ""

        if titleProp is not None:
            title = amlquery.get_attr(item, titleProp)

        if linkProp is not None:
            link = amlquery.get_attr(item, linkProp)

        if title != "" and link != "":
            urls.append(title + " (" + link + ")")
        elif link != "":
            urls.append("(" + link + ")")

    if len(urls) == 0:
        urls.append("")

    return urls


def clean_and_format(input_values):
    def cleaner(value):
        if isinstance(value, list) or isinstance(value, tuple):
            return sorted(list(map(cleaner, value)))
        else:
            return str(value).replace("&amp;", "&").replace(" -> ", "=")

    input_values = map(cleaner, input_values)

    return [
        "|".join(value) if isinstance(value, list) else value for value in input_values
    ]


def get_model_fad_connected_occs(model):
    high_level_fad_func = {}
    superior_func = amlquery.get_superior_defs(model["id"])

    if superior_func:
        superior_func = list(superior_func.values())[0]
        superior_fad = amlquery.get_assigned_models(superior_func, "MT_FUNC_ALLOC_DGM")

        if superior_fad:
            superior_fad = superior_fad[0]

            high_level_fad_func = list(amlquery.filter_occs_by_symbol(superior_fad))
            
            #if high_level_fad_func:
            #    connected_occs = high_level_fad_func[0].get('occs',{})
                
            #    connected_occs = amlquery.get_connected_occs(high_level_fad_func[0])

    return high_level_fad_func




# =============================================================================
# Debug /DEV
# =============================================================================

#model = models.get('Model.5HAW9lsVsE4-u-L') #VC
#model = models.get('Model.-SPTU0XPAjz-u-L') #BPMN
#item = model_attrs[1]

#from module_attributes.attributeHandler import AttributeHandler


#Get Diagram and Element Level Data from Signavio Workspace Setting
#Required: ARIS ST Mapping to every Signavio Element


# =============================================================================
# 
# =============================================================================
models = amlquery.find_models(model_types)


report_data = []


for model_id, model in models.items():
    
    #Diagram Level Data
    print('-------')
    print(model['name'] + ' (' + model['type'] + ')')
    row_entry_dict = {}
    row_entry_dict['Path'] = model.get('path','')
    row_entry_dict['Model Id'] = model.get('id','')
    row_entry_dict['Model Name'] = model.get('name','')
    row_entry_dict['ARIS GUID'] = model.get('guid','')
    row_entry_dict['Stencil'] = model.get('type','')
    
    
    model_level_attributes = model.get('attrs',{})
    for attribute_name, attribute_value in model_level_attributes.items():
        row_entry_dict[attribute_name] = attribute_value
    
    report_data.append(row_entry_dict)
    
    
    #Model Level Glossary Entries
    model_fad_connected_occs = get_model_fad_connected_occs(model)
    glossary_occs = amlquery.filter_occs_by_symbol(model_fad_connected_occs)
    print('Model Level Glossary : ' + str(glossary_occs))
    
    if glossary_occs:
        for occ in glossary_occs:
            symbol = occ.get('symbol')
            if symbol != 'ST_FUNC': #Name of Diagram
                value = amlquery.get_occ_name(occ)
                row_entry_dict[symbol] = value



    #Element Level Data
    elements = list(amlquery.filter_occs_by_symbol(model))
    for element in elements:
        
        row_entry_dict = {}
        
        symbol = element.get('symbol')
        aris_type = element.get('aris_type')
        element_name = amlquery.get_occ_name(element)
        print(symbol + ' -> ' + element_name  + ' (' + aris_type + ')')
        
        object_definition = amlquery.get_obj_def(element)
        element_level_attributes = object_definition.get("attrs", {})
   

        row_entry_dict['Path'] = model.get('path','')
        row_entry_dict['Model Id'] = model.get('id','')
        row_entry_dict['Model Name'] = model.get('name','')
        row_entry_dict['ARIS GUID'] = element.get('id','')
        row_entry_dict['Stencil'] = symbol
        row_entry_dict['Element Name'] = element_name
        
        #Get Standard Attributes
        for attribute_name, attribute_value in element_level_attributes.items():
            row_entry_dict[attribute_name] = attribute_value
        
        
        #Get all connected Glossary Elements
        #func_connected_occs = amlquery.get_connected_occs(element)
        fad_func_occ = amlquery.get_fad_func_occ(element) #extend with func_connected_occs
        
        #func_connected_occs, fad_func_occ = get_func_connected_occs(element)     
        #row_entry_dict['func_connected_occs'] = str(func_connected_occs)
        #row_entry_dict['fad_func_occ'] = str(fad_func_occ)
    
        #Element Level Glossary Entries
        fad_connections = amlquery.get_connections(fad_func_occ)
        for obj_occ, cxn_def_keys in fad_connections.items():
            for cxn_def_key in cxn_def_keys:
                glossary_information = amlquery.cxns.get(cxn_def_key)
                object_defintion_id = glossary_information.get('def','')
                glossary_information_type = glossary_information.get('type','') #'CT_HAS_CONSLT_ROLE_IN_2'
                print(glossary_information_type)
                object_defition = amlquery.defs.get(object_defintion_id)
                glossary_title = object_defition.get('name')
                print(glossary_title)
                glossary_type = object_defition.get('type')    # OT_PERS_TYPE
                print(glossary_type)
                glossary_symbol = object_defition.get('symbol')  #'ST_EMPL_TYPE'
                print(glossary_symbol)
                attributes = object_defition.get('attrs')
                path = object_defition.get('path') #Library/Roles
                
                row_entry_dict[glossary_information_type+';'+glossary_symbol] = glossary_title



        report_data.append(row_entry_dict)

report_data = sorted(report_data, key=lambda k: (k['Path'], k['Model Name'], k['ARIS GUID'])) #Sort report entries
path = Excel.create_v2(report_name='XML Report', report_data=report_data, special_color_attributes=['Path', 'Model Id', 'Model Name', 'ARIS GUID', 'Element Name', 'Stencil'])
    

