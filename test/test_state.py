"""
// SPDX-License-Identifier: Apache-2.0
// Copyright IBM Corp. 2023
"""

"""
Test SDK code functions

"""
import uuid
import json
from pathlib import Path
import os
import shutil
import pytest
# change working directory for test config/application.yaml
os.chdir("./test")

from ibm_pathfinder_sdk import eventpublisher as msgObject , pathfinderconfig, pfmodelclasses

class NULL_NAMESPACE:
    bytes = b''



# if therean existing class model load it like
# from pfmodelclasses import pathfinderClass 

# or create your own classes on your own model you need
class SystemTest(pfmodelclasses.SystemEntity):
    def __init__(self, edf_id):
        self.json_schema_ref = "urn:demo.for.testonly:systemtest:1.0.0"
        self.edf_id = edf_id
    def setName(self,name):
        self.name = name
    def setDescription(self,description):
        self.description = description 
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)  

class EnvironmentTest(pfmodelclasses.SystemEntity):
    def __init__(self, edf_id):
        self.json_schema_ref = "urn:demo.for.testonly:environmenttest:1.0.0"
        self.edf_id = edf_id
    def setName(self,name):
        self.name = name
    def setDescription(self,description):
        self.description = description     
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)     

class RelatedTest(pfmodelclasses.SystemRelationship):
    def __init__(self, from_edf_id, to_edf_id):
        self.json_schema_ref = "urn:demo.for.testonly:relatedtest:1.0.0"
        self.from_edf_id = from_edf_id
        self.to_edf_id = to_edf_id
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)



def test_compare_state():
    UNIQUE_CONNECTOR_ID = "my-connector-test01"
    PATHFINDER_CONNECTOR_STOP_SIGNAL = "GO"
    CONNECTOR_STATE_DIR = "./connector-state"
    pathfinderconfig.CONNECTOR_STATE = "file"
    if not os.path.exists(CONNECTOR_STATE_DIR):
        os.makedirs(CONNECTOR_STATE_DIR)
    pathfinderconfig.CONNECTOR_STATE_PATH = "./connector-state"
    
    conMsgObject =  msgObject.ConMsgObjectBase()
    connectorUuid = str(uuid.uuid3(NULL_NAMESPACE, UNIQUE_CONNECTOR_ID))
    connectorType = "PYTHON_TEST"
    event = pfmodelclasses.SystemEvent(connectorUuid, connectorType)
    
    environmentName = "Server Room 001"
    environemtEdfId = (str(uuid.uuid3(NULL_NAMESPACE,str(environmentName))))
    envObj = EnvironmentTest(environemtEdfId)
    envObj.setName(environmentName)
    envObj.setDescription("My demo room")
    event.payload = envObj
    conMsgObject.publishEvent(event)

	# write 10 entity related (10) to the environment
    for i in range(1, 11):
        systemName = str("System-" + str(i))
        systemEdfId = (str(uuid.uuid3(NULL_NAMESPACE,systemName)))
        sysObj = SystemTest(systemEdfId)
        sysObj.setName(systemName) 
        event.payload = sysObj
        conMsgObject.publishEvent(event)
        relatedObj = RelatedTest(systemEdfId,environemtEdfId)
        event.payload = relatedObj
        conMsgObject.publishEvent(event)
        
	# delete entity 10	
    systemName = str("System-" + str(10))
    systemEdfId = (str(uuid.uuid3(NULL_NAMESPACE,systemName)))
    sysObj = SystemTest(systemEdfId)
    sysObj.setName(systemName) 
    event.payload = sysObj
    event.event_type = "delete"
    conMsgObject.publishEvent(event)
    
	#delete relation to environment
    relatedObj = RelatedTest(systemEdfId,environemtEdfId)
    event.payload = relatedObj
    event.event_type = "delete"
    conMsgObject.publishEvent(event)
    

    conMsgObject.deleteUnusedEvents(event)
    conMsgObject.saveLastState()
    
    f = open(CONNECTOR_STATE_DIR + "/connectorstate.json")
    state = json.load(f)
    assert 1 == len(state["urn:demo.for.testonly:environmenttest:1.0.0"])
    assert 9 == len(state["urn:demo.for.testonly:systemtest:1.0.0"])
    assert 9 == len(state["urn:demo.for.testonly:relatedtest:1.0.0"])



def test_delete_unused():
    UNIQUE_CONNECTOR_ID = "my-connector-test01"
    PATHFINDER_CONNECTOR_STOP_SIGNAL = "GO"
    CONNECTOR_STATE_DIR = "./connector-state"
    pathfinderconfig.CONNECTOR_STATE = "file"
    if not os.path.exists(CONNECTOR_STATE_DIR):
        os.makedirs(CONNECTOR_STATE_DIR)
    pathfinderconfig.CONNECTOR_STATE_PATH = "./connector-state"
    
    conMsgObject =  msgObject.ConMsgObjectBase()
    connectorUuid = str(uuid.uuid3(NULL_NAMESPACE, UNIQUE_CONNECTOR_ID))
    connectorType = "PYTHON_TEST"
    event = pfmodelclasses.SystemEvent(connectorUuid, connectorType)
    
    environmentName = "Server Room 001"
    environemtEdfId = (str(uuid.uuid3(NULL_NAMESPACE,str(environmentName))))
    envObj = EnvironmentTest(environemtEdfId)
    envObj.setName(environmentName)
    envObj.setDescription("My demo room")
    event.payload = envObj
    conMsgObject.publishEvent(event)
    
    count = conMsgObject.deleteUnusedEvents(event)
    conMsgObject.saveLastState()
    print(count)
    assert 18==count
    
def test_cleanUpTestDir():
    # delete connector-state directory including the state file
    shutil.rmtree("connector-state")
    assert 1==1	
