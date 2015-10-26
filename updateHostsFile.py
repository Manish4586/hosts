#!/usr/bin/env python

# Script originally written by Ben Limmer
# https://github.com/l1m5
#
# Modified by Zaur Molotnikov
# https://github.com/qutorial/hosts 
#
# This simple Python script will combine all the host files you provide
# as sources into one, unique host file to keep you internet browsing happy.

#Python 2 compatibility
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import platform
import re
import string
import subprocess
import sys
import tempfile

try:
	from urllib.parse import urlparse, urlencode
	from urllib.request import urlopen, Request
	from urllib.error import HTTPError
except ImportError:
	from urlparse import urlparse
	from urllib import urlencode
	from urllib2 import urlopen, Request, HTTPError


Python3=False;

cur_version = sys.version_info
if cur_version >= (3, 0):
	Python3=True;
   
def myInput(msg=""):
	if Python3:
		return input(msg);
	else:
		return raw_input(msg);
		

# Project Settings
BASEDIR_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(BASEDIR_PATH, 'data')
DATA_FILENAMES = 'hosts'
UPDATE_URL_FILENAME = 'update.info'
SOURCES = os.listdir(DATA_PATH)
README_TEMPLATE = os.path.join(BASEDIR_PATH, 'readme_template.md')
README_FILE = os.path.join(BASEDIR_PATH, 'readme.md')
#0.0.0.0 works in the same way but is more confusing
TARGET_HOST = '127.0.0.1'

# Exclusions
EXCLUSION_PATTERN = '([a-zA-Z\d-]+\.){0,}' #append domain the end

# Common domains to exclude
COMMON_EXCLUSIONS = ['hulu.com']

# Global vars
exclusionRegexs = []
numberOfRules = 0

def main():
	promptForUpdate()
	promptForExclusions()
	mergeFile = createInitialFile()
	finalFile = removeDups(mergeFile)
	finalizeFile(finalFile)
	updateReadme(numberOfRules)
	printSuccess('Success! Your shiny new hosts file has been prepared.\nIt contains ' + "{:,}".format( numberOfRules ) + ' unique entries.')

	promptForMove(finalFile)

# Prompt the User
def promptForUpdate():
	response = query_yes_no("Do you want to update all data sources?")
	if (response == "yes"):
		updateAllSources()
	else:
		print ('OK, we\'ll stick with what we\'ve  got locally.')

def promptForExclusions():
	response = query_yes_no("Do you want to exclude any domains?\n" +
							"For example, hulu.com video streaming must be able to access " +
							"its tracking and ad servers in order to play video.", default="no")
	if (response == "yes"):
		displayExclusionOptions()
	else:
		print ('OK, we won\'t exclude any domains.')

def promptForMoreCustomExclusions():
	response = query_yes_no("Do you have more domains you want to enter?")
	if (response == "yes"):
		return True
	else:
		return False

def promptForMove(finalFile):
  response = query_yes_no("Do you want to replace your existing hosts file with the newly generated file?", default="no")
  if (response == "yes"):
    moveHostsFileIntoPlace(finalFile)
  else:
    return False
# End Prompt the User

# Exclusion logic
def displayExclusionOptions():
	for exclusionOption in COMMON_EXCLUSIONS:
		response = query_yes_no("Do you want to exclude the domain " + exclusionOption + " ?")
		if (response == "yes"):
			excludeDomain(exclusionOption)
		else:
			continue
	response = query_yes_no("Do you want to exclude any other domains?")
	if (response == "yes"):
		gatherCustomExclusions()

def gatherCustomExclusions():
	while True:
		domainFromUser = myInput("Enter the domain you want to exclude (e.g. facebook.com): ")
		if (isValidDomainFormat(domainFromUser)):
			excludeDomain(domainFromUser)
		if (promptForMoreCustomExclusions() == False):
			return

def excludeDomain(domain):
	exclusionRegexs.append(re.compile(EXCLUSION_PATTERN + domain))

def matchesExclusions(strippedRule):
	strippedDomain = strippedRule.split()[1]
	for exclusionRegex in exclusionRegexs:
		if exclusionRegex.search(strippedDomain):
			return True
	return False
# End Exclusion Logic


# This function handles both Python2 and Python3
def getFileByUrl(url):
	try:		
		f = urlopen(url)
		return f.read().decode("UTF-8")		
	except:
		print ("Problem getting file: ", url);
		raise
	
    

# Update Logic
def updateAllSources():
	for source in SOURCES:
		updateURL = getUpdateURLFromFile(source)
		if (updateURL == None):
			continue;
		print ('Updating source ' + source + ' from ' + updateURL)
		updatedFile = getFileByUrl(updateURL);
		updatedFile = updatedFile.replace('\r', '') #get rid of carriage-return symbols

		dataFile = open(os.path.join(DATA_PATH, source, DATA_FILENAMES), 'w')
		if Python3:
			dataFile.write(updatedFile)
		else:
			dataFile.write(updatedFile.encode("UTF-8"))
		dataFile.close()

def getUpdateURLFromFile(source):
	pathToUpdateFile = os.path.join(DATA_PATH, source, UPDATE_URL_FILENAME)
	if os.path.exists(pathToUpdateFile):
		updateFile = open(pathToUpdateFile, 'r')
		retURL = updateFile.readline().strip()
		updateFile.close()
	else:
		retURL = None
		printFailure('Warning: Can\'t find the update file for source ' + source + '\n' +
					 'Make sure that there\'s a file at ' + pathToUpdateFile)
	return retURL
# End Update Logic

# File Logic
def createInitialFile():
	mergeFile = tempfile.NamedTemporaryFile()	
	for source in SOURCES:
		curFile = open(os.path.join(DATA_PATH, source, DATA_FILENAMES), 'r')
		if Python3:
			mergeFile.write(bytes('\n# Begin ' + source + '\n', 'UTF-8'))
			mergeFile.write(bytes(curFile.read(), 'UTF-8'))
			mergeFile.write(bytes('\n# End ' + source + '\n', 'UTF-8'))
		else:
			mergeFile.write(str('\n# Begin ' + source + '\n').encode('UTF-8'))
			mergeFile.write(curFile.read())
			mergeFile.write(str('\n# End ' + source + '\n').encode( 'UTF-8'))
	return mergeFile

def removeDups(mergeFile):
	global numberOfRules

	finalFile = open(os.path.join(BASEDIR_PATH, 'hosts'), 'r+')
	mergeFile.seek(0) # reset file pointer

	hostnames = set()
	hostnames.add("localhost")
	for line in mergeFile.readlines():
		line = line.decode("UTF-8")
		
		# Comments and empty lines
		if line[0] == '#' or re.match(r'^\s*$', line[0]):
			try:#Python2
				finalFile.write(line.encode('UTF-8')) #maintain the comments for readability				
			except: #Python3				
				finalFile.write(line) #maintain the comments for readability
			continue

		strippedRule = stripRule(line) #strip comments
		if matchesExclusions(strippedRule):
			continue
		
		hostname, normalizedRule = normalizeRule(strippedRule) # normalize rule

		if normalizedRule and (hostname not in hostnames):
			finalFile.write(normalizedRule)
			hostnames.add(hostname)
			numberOfRules += 1

	mergeFile.close()

	return finalFile

def normalizeRule(rule):
	result = re.search(r'^[ \t]*(\d+\.\d+\.\d+\.\d+)\s+([\w\.-]+)(.*)',rule)
	if result:
		target, hostname, suffix = result.groups()
		if len(suffix) > 0:
                        print("Ignoring a suffix : ", suffix, " in a rule ", rule);
		hostname = hostname.lower() # explicitly lowercase hostname
		return hostname, "%s %s\n" % (TARGET_HOST, hostname)
	print ('Non-standard rule is passed: ', rule)
	return None, None

def finalizeFile(finalFile):
	writeOpeningHeader(finalFile)
	finalFile.close()

# Some sources put comments around their rules, for accuracy we need to strip them
# the comments are preserved in the output hosts file
def stripRule(line):
	splitLine = line.split()
	if (len(splitLine) < 2) :
		printFailure('A line in the hostfile is going to cause problems because it is nonstandard\n' +
					 'The line reads ' + str(line) + ' please check your data files. Maybe you have a comment without a #?')
		sys.exit()
	return splitLine[0] + ' ' + splitLine[1]

def writeOpeningHeader(finalFile):
	global numberOfRules
	finalFile.seek(0) #reset file pointer
	fileContents = finalFile.read(); #save content
	finalFile.seek(0) #write at the top
	finalFile.write('# This file is a merged collection of hosts from reputable sources,\n')
	finalFile.write('# with a dash of crowd sourcing via Github\n#\n')
	finalFile.write('# Project home page: https://github.com/StevenBlack/hosts\n#\n')
	finalFile.write('# Current sources:\n')
	for source in SOURCES:
		finalFile.write('#    ' + source + '\n')
	finalFile.write('#\n')
	finalFile.write('# Merging these sources produced ' + "{:,}".format( numberOfRules ) + ' unique entries\n')
	finalFile.write('# ===============================================================\n')
	finalFile.write('\n')
	finalFile.write('127.0.0.1 localhost\n')
	finalFile.write('\n')
	
	preamble = os.path.join(BASEDIR_PATH, "preamble.txt");
	if os.path.isfile(preamble):
		with open(preamble, "r") as f:
			finalFile.write(f.read());
	
	finalFile.write(fileContents)

def updateReadme(numberOfRules):
	with open(README_FILE, "wt") as out:
		for line in open(README_TEMPLATE):
			out.write(line.replace('@NUM_ENTRIES@', "{:,}".format( numberOfRules )))

def moveHostsFileIntoPlace(finalFile):
	if (os.name == 'posix'):
		print ('Moving the file requires administrative privileges. You might need to enter your password.')
		if(subprocess.call(["/usr/bin/sudo", "cp", os.path.abspath(finalFile.name), "/etc/hosts"])):
			printFailure("Moving the file failed.")
		print ('Flushing the DNS Cache to utilize new hosts file...')
		if (platform.system() == 'Darwin'):
			if(subprocess.call(["/usr/bin/sudo", "killall", "-HUP", "mDNSResponder"])):
				printFailure("Flushing the DNS Cache failed.")
		else:
			if os.path.isfile("/etc/rc.d/init.d/nscd"):
				if(subprocess.call(["/usr/bin/sudo", "/etc/rc.d/init.d/nscd", "restart"])):
					printFailure("Flushing the DNS Cache failed.")
			else:
				print("Flushing seems to happen automatically on this system")
	elif (os.name == 'nt'):
		print ('Automatically moving the hosts file in place is not yet supported.')
		print ('Please move the generated file to %SystemRoot%\system32\drivers\etc\hosts')

# End File Logic

# Helper Functions
## {{{ http://code.activestate.com/recipes/577058/ (r2)
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":"yes",   "y":"yes",  "ye":"yes",
             "no":"no",     "n":"no"}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(colorize(question, colors.PROMPT) + prompt)
        choice = myInput().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            printFailure("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")
## end of http://code.activestate.com/recipes/577058/ }}}

def isValidDomainFormat(domain):
	if (domain == ''):
		print ("You didn\'t enter a domain. Try again.")
		return False
	domainRegex = re.compile("www\d{0,3}[.]|https?")
	if (domainRegex.match(domain)):
		print ("The domain " + domain + " is not valid. Do not include www.domain.com or http(s)://domain.com. Try again.")
		return False
	else:
		return True

# Colors
class colors:
    PROMPT 	= '\033[94m'
    SUCCESS = '\033[92m'
    FAIL 	= '\033[91m'
    ENDC 	= '\033[0m'

def colorize(text, color):
	return color + text + colors.ENDC

def printSuccess(text):
	print (colorize(text, colors.SUCCESS))

def printFailure(text):
	print (colorize(text, colors.FAIL))
# End Helper Functions

if __name__ == "__main__":
	main()
