#! /usr/bin/python
""" Copyright 2015 Akamai Technologies, Inc. All Rights Reserved.
 
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.

 You may obtain a copy of the License at 

    http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.

Sample client 
In order to use this papi client you will need to have access turned
on for your account.  Send the contract IDs you want activated in a 
request to open-developer@akamai.com.

This script pulls the contract groups, properties for that group, and
products for that contract.

Please send any comments, questions or ideas to open-developer@akamai.com

Thanks!
The Akamai Developer Relations Team

"""

import requests, logging, json, random, sys, re
from random import randint
from akamai.edgegrid import EdgeGridAuth
from config import EdgeGridConfig
from urlparse import urljoin
import urllib
from subprocess import call
import os
session = requests.Session()
debug = False
section_name = "papi"

# If all parameters are set already, use them.  Otherwise
# use the config
try:
	config = EdgeGridConfig({"verbose":False},section_name)
except:
  error_msg = "ERROR: No section named %s was found in your ~/.edgerc file\n" % section_name
  error_msg += "ERROR: Please generate credentials for the script functionality\n"
  error_msg += "ERROR: and run 'gen_edgerc %s' to generate the credential file\n" % section_name
  sys.exit(error_msg)

if config.debug or config.verbose:
	debug = True

# Enable debugging for the requests module
if debug:
  import httplib as http_client
  http_client.HTTPConnection.debuglevel = 1
  logging.basicConfig()
  logging.getLogger().setLevel(logging.DEBUG)
  requests_log = logging.getLogger("requests.packages.urllib3")
  requests_log.setLevel(logging.DEBUG)
  requests_log.propagate = True


# Set the config options
session.auth = EdgeGridAuth(
            client_token=config.client_token,
            client_secret=config.client_secret,
            access_token=config.access_token
)

if hasattr(config, 'headers'):
	session.headers.update(config.headers)

baseurl = '%s://%s/' % ('https', config.host)

def getResult(endpoint, parameters=None):
  if parameters:
    parameter_string = urllib.urlencode(parameters)
    path = ''.join([endpoint + '?',parameter_string])
  else:
    path = endpoint
  endpoint_result = session.get(urljoin(baseurl,path))
  httpErrors(endpoint_result.status_code, path, endpoint_result.json())
  if debug: print ">>>\n" + json.dumps(endpoint_result.json(), indent=2) + "\n<<<\n"
  return endpoint_result.json()

def httpErrors(status_code, endpoint, result):
  if status_code == 403:
                error_msg =  "ERROR: Call to %s failed with a 403 result\n" % endpoint
                error_msg +=  "ERROR: This indicates a problem with authorization.\n"
                error_msg +=  "ERROR: Please ensure that the credentials you created for this script\n"
                error_msg +=  "ERROR: have the necessary permissions in the Luna portal.\n"
                error_msg +=  "ERROR: Problem details: %s\n" % result["detail"]
                exit(error_msg)

  if status_code in [400, 401]:
                error_msg =  "ERROR: Call to %s failed with a %s result\n" % (endpoint, status_code)
                error_msg +=  "ERROR: This indicates a problem with authentication or headers.\n"
                error_msg +=  "ERROR: Please ensure that the .edgerc file is formatted correctly.\n"
                error_msg +=  "ERROR: If you still have issues, please use gen_edgerc.py to generate the credentials\n"
                error_msg +=  "ERROR: Problem details: %s\n" % result["detail"]
                exit(error_msg)

  if status_code in [404]:
                error_msg =  "ERROR: Call to %s failed with a %s result\n" % (endpoint, status_code)
                error_msg +=  "ERROR: This means that the page does not exist as requested.\n"
                error_msg +=  "ERROR: Please ensure that the URL you're calling is correctly formatted\n"
                error_msg +=  "ERROR: or look at other examples to make sure yours matches.\n"
                error_msg +=  "ERROR: Problem details: %s\n" % result["detail"]
                exit(error_msg)

  error_string = None
  if "errorString" in result:
               if result["errorString"]:
                       error_string = result["errorString"]
  else:
    for key in result:
      if type(key) is not str:
        continue
      if type(result[key]["errorString"]) is str:
        error_string = result[key]["errorString"]
  if error_string:
                error_msg =  "ERROR: Call caused a server fault.\n"
                error_msg +=  "ERROR: Please check the problem details for more information:\n"
                error_msg +=  "ERROR: Problem details: %s\n" % error_string
                exit(error_msg) 

def getGroup():
	"""
	Request the list of groups for the account.  Print out
	how many groups there are, then use the first group where
	the test property lives.

	"""
	print
	print "Requesting the list of groups for this account"

	groups_result = getResult('/papi/v0/groups')

	return (groups_result)

def getProperties(groupId, contractId):
	"""
	Get the properties for the associated group/contract combination
	"""
	print "Getting properties for group %s and contract %s" % (groupId, contractId)
	property_parameters = { "contractId":contractId, "groupId":groupId }
	property_result = getResult('/papi/v0/properties', property_parameters)
	
	if "properties" in property_result:
		property_items = property_result['properties']['items']
	else:
		property_items = []

	return (property_items)

def getPropertyInfo(propName, groupId, contractId):
	properties = getProperties(groupId, contractId)
	for property in properties:
		if property["propertyName"] == propName:
			return property

def getSingleProperty(propertyId, groupId, contractId ):
	"""
	Get the properties for the associated group/contract combination
	"""
	property_parameters = { "contractId":contractId, "groupId":groupId }
	property_result = getResult('/papi/v0/properties/%s/' % propertyId, 
								property_parameters)
	return (property_result)

def findProperty(propertyName, config):
	print "Propname is %s" % propertyName
	groups = getGroup()
	if config.prop and not config.groupId or not config.contractId and "groups" in groups:
		groups = getGroup()["groups"]["items"]
	else:
		groups = [{	
					"groupId":config.groupId,
				  	"contractIds":[config.contractId]
				}]
	for group in groups:
		groupId = group["groupId"]
		if "contractIds" in group:
			for contractId in group["contractIds"]:
				if propertyName:
					property = getPropertyInfo(
									propertyName, 
									groupId, 
									contractId)
					return property
				else:
					print "Need a property to make this go."
					exit(0)

def getRealValue(version, property):
	if version == "STAGING":
		return property["stagingVersion"]
	if version == "PRODUCTION":
		return property["productionVersion"]
	if version == "LATEST":
		return property["latestVersion"]
	return version

def getPropertyVersion(property, version):
	result = {}
	property_parameters = { "contractId":property["contractId"],  "groupId":property["groupId"] }
	# We've got to get metadata, hostnames, and rules

	result_properties = getResult('/papi/v0/properties/%s/versions/%s'
								% (property["propertyId"], version),
								property_parameters)
	if "versions" not in result_properties:
		return
	result["meta"] = result_properties["versions"]["items"][0]

	hostname_results = getResult('/papi/v0/properties/%s/versions/%s/hostnames/'
								% (property["propertyId"], version),
								property_parameters)
	if "hostnames" in hostname_results and "items" in hostname_results["hostnames"] :
		if len(hostname_results["hostnames"]["items"])> 0:
			result["hostnames"] = hostname_results["hostnames"]["items"][0]

	rules_results = getResult('/papi/v0/properties/%s/versions/%s/rules/'
								% (property["propertyId"], version),
								property_parameters)
	if "rules" in rules_results:
		result["rules"]= rules_results["rules"]

	#print json.dumps(result, indent=2)
	return (result)	

def getDiff(from_ver, from_property, to_ver, to_property):
	from_ver = getRealValue(from_ver, from_property)
	to_ver = getRealValue(to_ver, to_property)

	print "Getting difference between version %s and %s" % (from_ver, to_ver)
	from_content = getPropertyVersion(from_property, from_ver)
	to_content = getPropertyVersion(to_property, to_ver)

	version_diff = {"rules":{},"meta":{},"hostnames":{}}
	top_from_ver = "%s VERSION %s" % (from_property["propertyName"], from_ver)
	top_to_ver = "%s VERSION %s" % (to_property["propertyName"], to_ver)
	diff = compareDeeply(from_content, to_content, version_diff, top_from_ver, top_to_ver)
	return diff

def compareDeeply(from_version, to_version, version_diff, top_from_ver, top_to_ver):
	if from_version == to_version:
		return
	if type(from_version) in [str,int,unicode, bool]:
		version_diff[top_from_ver] = from_version
		version_diff[top_to_ver] = to_version
		return version_diff

	if type(from_version) == list:
		version_diff[top_from_ver] = []
		version_diff[top_to_ver] = []
		for item in from_version:
			if item in to_version:
				continue
			version_diff[top_from_ver].append(item)
		for item in to_version:
			if item in from_version:
				continue
			version_diff[top_to_ver].append(item)
		return version_diff

	
	for key in from_version:
		if key not in version_diff:
			version_diff[key] = {}
		if key not in to_version:
			version_diff[key][top_from_ver] = from_version[key]
			continue
		else:
			diff_value = compareDeeply(from_version[key], to_version[key], version_diff[key], top_from_ver, top_to_ver)
			if diff_value:
				version_diff[key] = diff_value

	for keys in to_version:
		if key not in from_version:
			version_diff[key][top_to_ver] = to_version[key]
			continue

	return version_diff

if __name__ == "__main__":
	#1) Pull all groups/contracts
	if not os.path.exists("gitcache"):
		os.makedirs("gitcache")
	os.chdir("gitcache")
	call(["git", "init"])
	hostnames = open('hostnames', 'w+')
	meta = open('meta', 'w+')
	meta.write(" ")
	rules = open('rules', 'w+')
	rules.write(" ")
	call(["git", "add", "meta", "rules", "hostnames"])
	call(["git", "commit", "-a", "-m", "Initializing repository with a clean slate"])

	groupInfo = getGroup()
	first_account = groupInfo["accountId"]
	first_account_string = re.search('act_(.+?)$', first_account) 
	first_account = first_account_string.group(1)
	groups = groupInfo["groups"]["items"]
	for group in groups:
		groupId = group["groupId"]
		print "GroupId = " + groupId
		if "contractIds" in group:
			for contractId in group["contractIds"]:
				properties = getProperties(groupId, contractId)
				for property in properties:
					call (["git", "checkout", "master"])
					call (["git", "checkout", "-b", property["propertyName"]])
					LATEST = property["latestVersion"]
					STAGING = property["stagingVersion"]
					PRODUCTION = property["productionVersion"]
					if not os.path.exists('branch'):
						with open('branch', 'w+') as file:
							file.write(json.dumps(property, indent=2))
							call(["git", "commit", "-a", "-m", "Metadata for " + property["propertyName"]])
							call(["git", "tag", property["propertyName"] + "_META"])
					print "Latest Version is %s for %s" % (property["latestVersion"], property["propertyName"])
					for version in range(1, property["latestVersion"]+1):
						property_version = getPropertyVersion(property, version)
						print ">>>\n" + json.dumps(property_version, indent=2) + "\n<<<\n"
						with open('hostnames', 'w+') as file:
							if "hostnames" in property_version:
								file.write(json.dumps(property_version["hostnames"], indent=2))
						with open('meta', 'w+') as file:
							if "meta" in property_version:
								file.write(json.dumps(property_version["meta"], indent=2))
						with open('rules', 'w+') as file:
							if "rules" in property_version:
								file.write(json.dumps(property_version["rules"], indent=2))
						if version == 1:
							call(["git", "add", "rules", "hostnames", "meta"])
						author = property_version["meta"]["updatedByUser"] 
						author_string = author + " <" + author + "@akamai.com>" 
						date = property_version["meta"]["updatedDate"]
						call(["git", "commit", "--author=" + author_string, "--date=" + date, "-a", "-m", "Version " + property["propertyName"] + " : " + str(version)])
						call(["git", "tag", property["propertyName"] + "@" + str(version)])
						if property_version == LATEST:
							call (["git", "tag", property["propertyName"] + "@" + "LATEST"])
						if property_version == STAGING:
							call (["git", "tag", property["propertyName"] + "@" + "STAGING"])
						if property_version == PRODUCTION:
							call (["git", "tag", property["propertyName"] + "@" + "PRODUCTION"])

					
						
