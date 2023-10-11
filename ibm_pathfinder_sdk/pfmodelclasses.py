"""
// SPDX-License-Identifier: Apache-2.0
// Copyright IBM Corp. 2023
"""

"""
This defines the basic event and relationship structures.


All entity classes must extend SystemEntity
All relationship classes must extend SystemRelationship

"""

import json  

class NULL_NAMESPACE:
    bytes = b''

class Object:
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

class SystemEvent:
    def __init__(self, connector_edf_id,connector_type):
        self.connector_edf_id = connector_edf_id
        self.connector_type = connector_type
        self.event_type =  "upsert"

        self.payload = Object()
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4) 

## event payload classes
class SystemEntity:
    def __init__(self):
        self.json_schema_ref = ""
        self.edf_id = ""
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4) 

class SystemRelationship:
    def __init__(self):
        self.json_schema_ref = ""
        self.from_edf_id = ""
        self.to_edf_id = ""       
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4) 

# Helpers to generate the keys for Kafka messages containing entities or relationships
class KafkaKeyEntity:
    def __init__(self):
        self.connector_edf_id = ""
        self.json_schema_ref = ""
        self.edf_id = ""
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4) 

class KafkaKeyRelationship:
    def __init__(self): 
        self.connector_edf_id = ""
        self.json_schema_ref = ""
        self.from_edf_id = ""
        self.to_edf_id = ""
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4) 




