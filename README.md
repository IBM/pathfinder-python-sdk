[![Build Status](https://app.travis-ci.com/IBM/pathfinder-python-sdk.svg?branch=main)](https://app.travis-ci.com/IBM/pathfinder-python-sdk)
[![Release](https://img.shields.io/github/v/release/IBM/pathfinder-python-sdk)](https://github.com/IBM/pathfinder-python-sdk/releases/latest)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ibm_pathfinder_sdk)](https://pypi.org/project/ibm_pathfinder_sdk/)
[![PyPI](https://img.shields.io/pypi/v/ibm_pathfinder_sdk)](https://pypi.org/project/ibm_pathfinder_sdk/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/ibm_pathfinder_sdk)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)



# pathfinder-python-sdk
The open source Pathfinder Python SDK allows you to build connectors for reporting metadata into Pathfinder.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Using the SDK](#using-the-sdk)
- [Open source @ IBM](#open-source--ibm)
- [Contributing](#contributing)
- [License](#license)

## Overview

 Modul Name | Usage | Class Name
--- | --- | ---
eventpublisher | Publishing to http registry endpoint | ConMsgObjectModelRegistry
eventpublisher | Publishing to kafka endpoint | ConMsgObjectKafka 
eventpublisher | Publishing to stdout | ConMsgObjectBase
pathfinderconfig | configuration | env var or application.yaml
pfmodelclasses | SystemEvent | SystemEvent
pfmodelclasses | SystemEvent.payload | SystemEntity
pfmodelclasses | SystemEvent.payload | SystemRelationship
pfmodelclasses | --Kafka key builder-- | --KafkaKeyEntity--
pfmodelclasses | --Kafka key builder-- | --KafkaKeyRelationship--

## Prerequisites
requirements.txt
```txt
ibm-pathfinder-sdk
```

## Installation
To install, use `pip`:

```shellscript
python -m pip install --upgrade ibm_pathfinder_sdk
```


## Using the SDK

Simple create a connector for pathfinder.
Crate your python env and create e.g python my_connector.py

```python
import uuid
import json
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



UNIQUE_CONNECTOR_ID = "my-connector-test01"
PATHFINDER_CONNECTOR_STOP_SIGNAL = "GO"

# use pf-model-registry
conMsgObject = msgObject.ConMsgObjectModelRegistry()
# If you like to write the events to stdout only, 
# because you don't have a running Pathfinder backend/registry, 
# use ConMsgObjectBase() instead. 
# conMsgObject =  msgObject.ConMsgObjectBase()

connectorUuid = str(uuid.uuid3(NULL_NAMESPACE, UNIQUE_CONNECTOR_ID))
connectorType = "PYTHON_EXAMPLE"
event = pfmodelclasses.SystemEvent(connectorUuid, connectorType)



environmentName = "Server Room 001"
environemtEdfId = (str(uuid.uuid3(NULL_NAMESPACE,str(environmentName))))

envObj = EnvironmentTest(environemtEdfId)
envObj.setName(environmentName)
envObj.setDescription("My demo room")

event.payload = envObj
# event setting, default is upsert
# event.event_type = "upsert"
# event.event_type = "delete" 
conMsgObject.publishEvent(event)


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






```

### Configuration
The configuration can be done in two variants, either environment variables or file-based.

To do it with environmental variables, export the variables and start python:
```shellscript
export OIDC_CLIENT_ENABLED=False
export K8S_TOKEN_AUTH=False
# if you use msgObject.ConMsgObjectBase(), you dont need this export
export PF_MODEL_REGISTRY_URL=http://<registry-url>:<port>/<api path>
# start your connector
python my_connector.py --env
```
To use a configuration file instead, create it as `config/application.yaml`.
This are the minimal parameters:
```yaml
stopMode: stop

pathfinder:
  kubernetesUrl: https://<cluster>:<port>
  url: http://<registry-url>:<port>/<api path>
  connector:
    state:
      type: local

k8sauth:
  enabled: False
oidc:
  enabled: False
```
Finally you can run the connector :
```shellscript
python my_connector.py
```



## Open source @ IBM
Find more open source projects on the [IBM Github Page](http://ibm.github.io/)

## License

This SDK is released under the Apache 2.0 license.
The license's full text can be found in [LICENSE](https://github.com/IBM/pathfinder-python-sdk/blob/main/LICENSE).
