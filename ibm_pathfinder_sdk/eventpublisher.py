"""
// SPDX-License-Identifier: Apache-2.0
// Copyright IBM Corp. 2023
"""

"""
Publishes metadata events to kafka or Pathfinder registry-gateway (http) endpoint.

"""
import requests
import logging
import time
import json
from os.path import exists
import ssl
import uuid
import boto3
from kafka import KafkaProducer


from requests.structures import CaseInsensitiveDict

from ibm_pathfinder_sdk import pfmodelclasses, pathfinderconfig

class NULL_NAMESPACE:
    bytes = b''

class ConMsgObjectBase:
    def __init__(self):
        self.connectorState = {}
        self.connectorState["delete"] = {}
        self.connectorState["state"] = {}
        self.loadLastState()
        self.allMessages = []
        self.validSchemas = []

    # update the state
    def updateState(self, event : pfmodelclasses.SystemEvent):
        if ( (str(pathfinderconfig.CONNECTOR_STATE).upper() != "NONE") and 
             (str(event.payload.__class__.__name__) != "ToDeleteEntity" and 
              str(event.payload.__class__.__name__) != "ToDeleteRelationship") ):
            if isinstance(event.payload.__class__.__base__(), pfmodelclasses.SystemEntity):
                eventId = event.payload.edf_id
            if isinstance(event.payload.__class__.__base__(), pfmodelclasses.SystemRelationship): 
                eventId = event.payload.from_edf_id + "|" + event.payload.to_edf_id
            # upsert update state only
            if ( event.event_type == "upsert"):
                if event.payload.json_schema_ref not in self.connectorState["state"]:
                    self.connectorState["state"][event.payload.json_schema_ref] = {} 
                self.connectorState["state"][event.payload.json_schema_ref][eventId] = str(uuid.uuid3(NULL_NAMESPACE, event.payload.toJSON()))
            # delete update state and delete/last run data
            if ( event.event_type == "delete"):
                if ( event.payload.json_schema_ref in self.connectorState["state"] and 
                     eventId in self.connectorState["state"][event.payload.json_schema_ref] ):
                    del self.connectorState["state"][event.payload.json_schema_ref][eventId]
                if ( event.payload.json_schema_ref in self.connectorState["delete"] and 
                     eventId in self.connectorState["delete"][event.payload.json_schema_ref] ):
                    del self.connectorState["delete"][event.payload.json_schema_ref][eventId]
        return 0 

    # delete events which not reported anymore
    def deleteUnusedEvents(self, event: pfmodelclasses.SystemEvent):
        logging.info("deleteUnusedEvents")
        class ToDeleteEntity(pfmodelclasses.SystemEntity):
            pass
        class ToDeleteRelationship(pfmodelclasses.SystemRelationship):
            pass

        event.event_type = "delete"
        deleted = 0

        # update the clean up data connectorState["delete"]
        for eventGroup in self.connectorState["state"]:
            for eventId in self.connectorState["state"][eventGroup]:
                if (eventGroup in self.connectorState["delete"]) and (eventId in self.connectorState["delete"][eventGroup]): 
                    del self.connectorState["delete"][eventGroup][eventId]            

        # delete all events exists in the connectorState["delete"]
        for eventGroup in self.connectorState["delete"]:
            for eventId in self.connectorState["delete"][eventGroup]:
                if "|" in eventId:
                    toDelete = ToDeleteRelationship()
                    toDelete.from_edf_id = str(eventId).split("|")[0]
                    toDelete.to_edf_id = str(eventId).split("|")[1]
                    toDelete.json_schema_ref = eventGroup 
                else:
                    toDelete = ToDeleteEntity()
                    toDelete.edf_id = eventId
                    toDelete.json_schema_ref = eventGroup
                event.payload = toDelete
                logging.debug(event.toJSON())
                self.publishEvent(event)
                deleted = deleted + 1
        return deleted

    # load last state of reported events
    def loadLastState(self):
        if str(pathfinderconfig.CONNECTOR_STATE).upper() == "S3":
            logging.info("Load last connector state from COS/S3 json file")
            s3Client = boto3.client("s3",
                        endpoint_url=pathfinderconfig.CONNECTOR_STATE_ENDPOINT_URL,
                        aws_access_key_id=pathfinderconfig.CONNECTOR_STATE_AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=pathfinderconfig.CONNECTOR_STATE_AWS_SECRET_ACCESS_KEY)
            try:
                connectorUuid = str(uuid.uuid3(NULL_NAMESPACE, pathfinderconfig.UNIQUE_CONNECTOR_ID))
                obj = s3Client.get_object(Bucket=pathfinderconfig.CONNECTOR_STATE_BUCKET, Key=connectorUuid + ".json")
                self.connectorState["delete"] = json.loads(obj['Body'].read().decode('utf-8'))
            except:
                self.connectorState["delete"] = {}
        else:
            logging.info("Load last connector state from json file")
            if exists(pathfinderconfig.CONNECTOR_STATE_PATH  +'/connectorstate.json'):
                with open(pathfinderconfig.CONNECTOR_STATE_PATH + '/connectorstate.json', 'r') as filehandle:
                    self.connectorState["delete"] = json.loads(filehandle.read())
        return 0

    # save last state of reported events
    def saveLastState(self):
        if str(pathfinderconfig.CONNECTOR_STATE).upper() == "S3":
            logging.info("Save connector state to COS/S3 json file")
            s3Client = boto3.client("s3",
                        endpoint_url=pathfinderconfig.CONNECTOR_STATE_ENDPOINT_URL,
                        aws_access_key_id=pathfinderconfig.CONNECTOR_STATE_AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=pathfinderconfig.CONNECTOR_STATE_AWS_SECRET_ACCESS_KEY)
            connectorUuid = str(uuid.uuid3(NULL_NAMESPACE, pathfinderconfig.UNIQUE_CONNECTOR_ID))
            s3Client.put_object(Body=json.dumps(self.connectorState["state"]), Bucket=pathfinderconfig.CONNECTOR_STATE_BUCKET, Key=connectorUuid + ".json")
        else:
            logging.info("Save connector state to json file")
            with open(pathfinderconfig.CONNECTOR_STATE_PATH + '/connectorstate.json', 'w') as filehandle:
                filehandle.write(json.dumps(self.connectorState["state"]))


            if pathfinderconfig.JSON_EXPORT_ENABLED:
                logging.info("Export published datat to json file")
                with open(pathfinderconfig.JSON_EXPORT_PATH + '/connector_export.json', 'w') as filehandle_export:
                    filehandle_export.write(json.dumps(self.allMessages))

    # report events if it not reported yet
    def eventReporting(self, event : pfmodelclasses.SystemEvent):
        unknowEvent = True
        if str(pathfinderconfig.CONNECTOR_STATE).upper() != "NONE" and event.event_type == "upsert":
            if isinstance(event.payload.__class__.__base__(), pfmodelclasses.SystemEntity):
                eventId = event.payload.edf_id
            if isinstance(event.payload.__class__.__base__(), pfmodelclasses.SystemRelationship):
                eventId = event.payload.from_edf_id + "|" + event.payload.to_edf_id

            try:
                if str(uuid.uuid3(NULL_NAMESPACE, event.payload.toJSON())) == self.connectorState["state"][event.payload.json_schema_ref][eventId]:
                    unknowEvent = False
            except:
                try:
                    if str(uuid.uuid3(NULL_NAMESPACE, event.payload.toJSON())) == self.connectorState["delete"][event.payload.json_schema_ref][eventId]:
                        unknowEvent = False
                except:
                    pass

        return unknowEvent

    # must be overwriten by ConMsgObjectModelRegistry or ConMsgObjectKafka
    def publishEvent(self, event: pfmodelclasses.SystemEvent):
        self.allMessages.append(json.loads(event.toJSON()))
        if self.eventReporting(event):
            print(event.toJSON())
            pass
        self.updateState(event)
        return 0



class ConMsgObjectModelRegistry(ConMsgObjectBase):
    def __init__(self):
        super().__init__()
        self.access_token = ""
        self.token_expires = time.time()
        self.validSchemas = []
        if pathfinderconfig.OIDC_CLIENT_ENABLED:
            logging.info("Pf-model-Registry mode")
            logging.info("Keycloak token endpoint: " + pathfinderconfig.KEYCLOAK_TOKEN_URL)
            logging.info("OIDC grant_type: " + pathfinderconfig.OIDC_CLIENT_GRANT_TYPE)
            logging.info("OIDC client_id: " + pathfinderconfig.OIDC_CLIENT_ID)
            self.getBearer()
        logging.info("Pf-model-registry url: " + pathfinderconfig.PF_MODEL_REGISTRY_URL)
        
        


 
    # Get Bearer token
    ################################
    def getBearer(self):
        logging.info("Bearer token request")
        data = ("client_id=" + pathfinderconfig.OIDC_CLIENT_ID +
                "&client_secret=" + pathfinderconfig.OIDC_CLIENT_SECRET +
                "&username=" + pathfinderconfig.OIDC_CLIENT_USER +
                "&password="  + pathfinderconfig.OIDC_CLIENT_USER_PASSWORD +
                "&grant_type=" + pathfinderconfig.OIDC_CLIENT_GRANT_TYPE)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}              
        r = requests.post(pathfinderconfig.KEYCLOAK_TOKEN_URL, data=data, headers=headers, verify=False)
        if r.status_code == 200:
            self.access_token = r.json()["access_token"]
            #logging.debug(r.json()["access_token"])
            self.token_expires = time.time() + r.json()["expires_in"]
        else:
            logging.error('OpenId bearer token request error ' + str(r.status_code))
            exit(1)
        return 0

    def getValidtoken(self):
        # check is token not expired / if delta < 1 minute get a new Bearer token
        if (self.token_expires - time.time()) < 60:
            self.getBearer()
        return self.access_token


    def getK8stoken(self):
        if not pathfinderconfig.K8S_TOKEN_AUTH_TOKEN:
            with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as file:
                pathfinderconfig.K8S_TOKEN_AUTH_TOKEN = file.read()
        else:    
            token = pathfinderconfig.K8S_TOKEN_AUTH_TOKEN
        return token

    def checkGroupIdExists(self, groupId):
        headers = CaseInsensitiveDict()
        headers["Accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        if pathfinderconfig.OIDC_CLIENT_ENABLED:
            headers["Authorization"] = "Bearer " + self.getValidtoken()
        else:
            if pathfinderconfig.K8S_TOKEN_AUTH:
                headers["Authorization"] = "SAToken " + self.getK8stoken()
        r = requests.get(pathfinderconfig.PF_MODEL_REGISTRY_URL + "/registry/schemagroups/" + groupId,  headers=headers, verify=False)
        if r.status_code == 404:
            logging.info("groupid " + groupId +  " not exists")
            data = {"descripton" : "autogenerated " + groupId}
            r = requests.put(pathfinderconfig.PF_MODEL_REGISTRY_URL + "/registry/schemagroups/" + groupId, data=json.dumps(data), headers=headers, verify=False)
            if r.status_code == 201:
                logging.info(groupId + "created")
            else:
                logging.error("registry error " + str(r.status_code))
        else:
            if r.status_code == 200:
                logging.info("groupid exists")
            else:
                logging.error("registry error " + str(r.status_code))
                exit(1)
        return 0


    def checkSchemaExists(self, groupId, schema, typePayload):
        headers = CaseInsensitiveDict()
        headers["Accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        if pathfinderconfig.OIDC_CLIENT_ENABLED:
            headers["Authorization"] = "Bearer " + self.getValidtoken()
        else:
            if pathfinderconfig.K8S_TOKEN_AUTH:
                headers["Authorization"] = "SAToken " + self.getK8stoken()
        r = requests.get(pathfinderconfig.PF_MODEL_REGISTRY_URL + "/registry/schemagroups/" + groupId + "/schemas/"+ schema,  headers=headers, verify=False)
        logging.info("checkSchemaExists check " + str(r.status_code))
        if r.status_code == 404:
            logging.info("schema " + schema + " in group " + schema + " not exists")
            data = {}
            data["$id"] = "urn:" + groupId + ":" + schema + ":1.0.0"
            data["$schema"] = "https://json-schema.org/draft/2020-12/schema"
            data["description"] = "None"
            if isinstance(typePayload(), pfmodelclasses.SystemEntity):
                data["description"] = schema + " entity"
            if isinstance(typePayload(), pfmodelclasses.SystemRelationship):
                data["description"] = "A " + schema + " relationship"
            data["type"] = "object"
            data["additionalProperties"] = True
            data["properties"] = {}
            data["required"] = []
            data["allOf"] = []
            data["$defs"] = {}

            if data["description"] == "None":
                logging.error("schema reference error")
                exit(1)
            else:
                if typePayload == "SystemEntity":
                    data["allOf"].append({"$ref": "urn:com.ibm.pathfinder.system:entity:1.0.0"})
                if typePayload == "SystemRelationship":
                    data["allOf"].append({"$ref": "urn:com.ibm.pathfinder.system:relationship:1.0.0"})


            r = requests.post(pathfinderconfig.PF_MODEL_REGISTRY_URL + "/registry/schemagroups/" + groupId + "/schemas/"+ schema, data=json.dumps(data), headers=headers, verify=False)
            if r.status_code < 300 :
                logging.info("Schema " + schema + " created --> HTTP STATUS CODE " + str(r.status_code))
            else: 
                logging.error("Schema " + schema + " creation error --> HTTP STATUS CODE " + str(r.status_code))
                exit(1)
        return 0


    def publishEvent(self,event : pfmodelclasses.SystemEvent):
        logging.info("publish event " + str(event.payload.__class__.__base__) + " schema ref " + str(event.payload.json_schema_ref))
        if (event.payload.json_schema_ref not in self.validSchemas):
            entityArray = event.payload.json_schema_ref.split(":")
            self.checkGroupIdExists(entityArray[1])
            self.checkSchemaExists(entityArray[1], entityArray[2], event.payload.__class__.__base__)
            self.validSchemas.append(event.payload.json_schema_ref)
        headers = CaseInsensitiveDict()
        headers["Accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        if pathfinderconfig.OIDC_CLIENT_ENABLED:
            headers["Authorization"] = "Bearer " + self.getValidtoken()
        else:
            if pathfinderconfig.K8S_TOKEN_AUTH:
                headers["Authorization"] = "SAToken " + self.getK8stoken()

        status_code = 200
        if self.eventReporting(event):
            r = requests.post(pathfinderconfig.PF_MODEL_REGISTRY_URL + "/publish/event", data=event.toJSON(), headers=headers, verify=False)
            logging.debug(event.toJSON() + "  --> HTTP STATUS CODE " + str(r.status_code))
            status_code = r.status_code
        self.allMessages.append(json.loads(event.toJSON()))
        if (status_code == 200):
            self.updateState(event)
        if status_code > 201:
            logging.error(event.toJSON() + "  --> HTTP STATUS CODE " + str(r.status_code))
        return r.status_code


class ConMsgObjectKafka(ConMsgObjectBase):
    def __init__(self):
        super().__init__()
        sasl_mechanism = 'SCRAM-SHA-512'
        security_protocol = 'SASL_SSL'
        # Create a new context using system defaults, disable all but TLS1.2
        context = ssl.create_default_context()
        context.options &= ssl.OP_NO_TLSv1
        context.options &= ssl.OP_NO_TLSv1_1
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        logging.info("Kafka direct mode")
        logging.info("Bootstrap_servers: " + pathfinderconfig.KAFKA_BROKER)
        logging.info("Kafka user: " + pathfinderconfig.KAFKA_USER)
        logging.info("Kafka topic " + pathfinderconfig.KAFKA_TOPIC)

        self.kafkaProducer = KafkaProducer(
                     bootstrap_servers= pathfinderconfig.KAFKA_BROKER,
                     sasl_plain_username = pathfinderconfig.KAFKA_USER,
                     sasl_plain_password = pathfinderconfig.KAFKA_PASSWORD,
                     ssl_context = context,
                     security_protocol = security_protocol,
                     sasl_mechanism = sasl_mechanism
                     )


    def publishEvent(self,event: pfmodelclasses.SystemEvent):
        kafkaKey = None
        logging.info("publish event " + str(event.payload.__class__.__base__) + " schema ref " + str(event.payload.json_schema_ref))
        if isinstance(event.payload.__class__.__base__(),  pfmodelclasses.SystemEntity): 
        #if event.payload.__class__.__base__  == pfmodelclasses.SystemEntity:
            kafkaKey = pfmodelclasses.KafkaKeyEntity()
            kafkaKey.connector_edf_id = event.connector_edf_id
            kafkaKey.json_schema_ref = event.payload.json_schema_ref
            kafkaKey.edf_id = event.payload.edf_id

        if isinstance(event.payload.__class__.__base__(),  pfmodelclasses.SystemEntity):
        #if event.payload.__class__.__base__  == pfmodelclasses.SystemRelationship:
            kafkaKey = pfmodelclasses.KafkaKeyRelationship()
            kafkaKey.connector_edf_id = event.connector_edf_id
            kafkaKey.json_schema_ref = event.payload.json_schema_ref
            kafkaKey.from_edf_id = event.payload.from_edf_id
            kafkaKey.to_edf_id = event.payload.to_edf_id
        logging.debug(kafkaKey.toJSON())
        logging.debug(event.toJSON())
        if self.eventReporting(event):
            self.kafkaProducer.send(pathfinderconfig.KAFKA_TOPIC, key=bytes(kafkaKey.toJSON(), encoding="utf-8"), value=bytes(event.toJSON(), encoding="utf-8"))
            self.kafkaProducer.flush()
        self.updateState(event)
        return 0

