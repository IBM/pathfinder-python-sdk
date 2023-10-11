"""
// SPDX-License-Identifier: Apache-2.0
// Copyright IBM Corp. 2023
"""

import os
import logging
import yaml
import sys

pathfinderargs = sys.argv[1:]

if "--env" in pathfinderargs:
    # Get all environment variables instat of value.yaml
    UNIQUE_CONNECTOR_ID=""

    # pf-model-registry
    K8S_TOKEN_AUTH = bool(os.getenv('K8S_TOKEN_AUTH',"False"))
    OIDC_CLIENT_ENABLED = bool(os.getenv('OIDC_CLIENT_ENABLED'))
    if OIDC_CLIENT_ENABLED:
        KEYCLOAK_TOKEN_URL = os.getenv('KEYCLOAK_TOKEN_URL')
        OIDC_CLIENT_ID = os.getenv('OIDC_CLIENT_ID')
        OIDC_CLIENT_SECRET = os.getenv('OIDC_CLIENT_SECRET')
        OIDC_CLIENT_USER = os.getenv('OIDC_CLIENT_USER')
        OIDC_CLIENT_USER_PASSWORD = os.getenv('OIDC_CLIENT_USER_PASSWORD')
        OIDC_CLIENT_GRANT_TYPE = os.getenv('OIDC_CLIENT_GRANT_TYPE')

    PF_MODEL_REGISTRY_URL = os.getenv('PF_MODEL_REGISTRY_URL')

    # kafka direct
    KAFKA_BROKER = os.getenv('KAFKA_BROKER')
    KAFKA_TOPIC = os.getenv('KAFKA_TOPIC')
    KAFKA_USER = os.getenv('KAFKA_USER')
    KAFKA_PASSWORD = os.getenv('KAFKA_PASSWORD')

    # connector state
    CONNECTOR_STATE=os.getenv('CONNECTOR_STATE')
    CONNECTOR_STATE_ENDPOINT_URL=os.getenv('CONNECTOR_STATE_ENDPOINT_URL')
    CONNECTOR_STATE_AWS_ACCESS_KEY_ID=os.getenv('CONNECTOR_STATE_AWS_ACCESS_KEY_ID')
    CONNECTOR_STATE_AWS_SECRET_ACCESS_KEY=os.getenv('CONNECTOR_STATE_AWS_SECRET_ACCESS_KEY')
    CONNECTOR_STATE_BUCKET=os.getenv('CONNECTOR_STATE_BUCKET')

    PATHFINDER_CONNECTOR_STOP_SIGNAL = os.getenv('PATHFINDER_CONNECTOR_STOP_SIGNAL','go')

    if os.getenv('CONNECTOR_STATE_PATH') is not None:
        CONNECTOR_STATE_PATH = os.getenv('CONNECTOR_STATE_PATH')
    else:
        CONNECTOR_STATE_PATH = "/tmp"


    if os.getenv('JSON_EXPORT_ENABLED',"false").upper() == "TRUE": 
        JSON_EXPORT_ENABLED = True
    else:
        JSON_EXPORT_ENABLED = False

    if os.getenv('JSON_EXPORT_PATH') is not None:
        JSON_EXPORT_PATH = os.getenv('JSON_EXPORT_PATH')
    else:
        JSON_EXPORT_PATH = "/tmp"

    # system
    CONNECTOR_LOGGING_LEVEL = os.getenv('CONNECTOR_LOGGING_LEVEL',"INFO")


    # set logging for all python components
    numeric_level = getattr(logging, CONNECTOR_LOGGING_LEVEL.upper(), 10)
    logging.basicConfig(format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=numeric_level)



else:
    yamlCfg = {}
    with open("config/application.yaml", "r") as stream:
        try:
            #print(yaml.safe_load(stream))
            yamlCfg = yaml.safe_load(stream)
            print(yamlCfg)
        except yaml.YAMLError as exc:
            print(exc)
    
    # Get environment variables
    
    if "id" in yamlCfg["pathfinder"]["connector"]:
        UNIQUE_CONNECTOR_ID = yamlCfg["pathfinder"]["connector"]["id"]
    else:
        UNIQUE_CONNECTOR_ID=""
    
    # pf-model-registry
    if ("k8sauth" in yamlCfg) and ("enabled" in yamlCfg["k8sauth"]):
        K8S_TOKEN_AUTH = bool(yamlCfg["k8sauth"]["enabled"])
    else:
        K8S_TOKEN_AUTH = False
    if ("k8sauth" in yamlCfg) and ("token" in yamlCfg["k8sauth"]):
        K8S_TOKEN_AUTH_TOKEN = yamlCfg["k8sauth"]["token"]

   
    if "enabled" in yamlCfg["oidc"]:
        OIDC_CLIENT_ENABLED = bool(yamlCfg["oidc"]["enabled"])
    else:
        OIDC_CLIENT_ENABLED = True
    if OIDC_CLIENT_ENABLED:    
        KEYCLOAK_TOKEN_URL = yamlCfg["oidc"]["authServerUrl"] + "/protocol/openid-connect/token"
        OIDC_CLIENT_ID = yamlCfg["oidc"]["clientId"]
        OIDC_CLIENT_SECRET = yamlCfg["oidc"]["clientSecret"]
        OIDC_CLIENT_GRANT_TYPE = "client_credentials"
        OIDC_CLIENT_USER = ""
        OIDC_CLIENT_USER_PASSWORD = ""

    
    PF_MODEL_REGISTRY_URL = yamlCfg["pathfinder"]["url"]
    
    # connector state
    CONNECTOR_STATE=yamlCfg["pathfinder"]["connector"]["state"]["type"]
    if CONNECTOR_STATE == "s3":
        CONNECTOR_STATE_ENDPOINT_URL= "https://" + yamlCfg["pathfinder"]["connector"]["state"]["service-endpoint"]
        CONNECTOR_STATE_AWS_ACCESS_KEY_ID=yamlCfg["pathfinder"]["connector"]["state"]["access-key"]
        CONNECTOR_STATE_AWS_SECRET_ACCESS_KEY=yamlCfg["pathfinder"]["connector"]["state"]["secret-key"]
        CONNECTOR_STATE_BUCKET=yamlCfg["pathfinder"]["connector"]["state"]["bucket-name"]
    
    PATHFINDER_CONNECTOR_STOP_SIGNAL = os.getenv('PATHFINDER_CONNECTOR_STOP_SIGNAL')

    if CONNECTOR_STATE == "file":
        CONNECTOR_STATE_PATH = "/opt/app-root/connectorstate"
    else:
        CONNECTOR_STATE_PATH = "/tmp"
        
    # no json export
    JSON_EXPORT_ENABLED = False
    JSON_EXPORT_PATH = "/tmp"
    
    # system
    CONNECTOR_LOGGING_LEVEL = os.getenv('CONNECTOR_LOGGING_LEVEL',"DEBUG")
    
    
    # set logging for all python components
    numeric_level = getattr(logging, CONNECTOR_LOGGING_LEVEL.upper(), 10)
    logging.basicConfig(format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=numeric_level)