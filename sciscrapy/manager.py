# -*- coding: utf-8 -*-

import os
from os import listdir
from os.path import isfile, join, isdir
from glob import glob
from collections import defaultdict
import sys
import re
import imp
import string
import inspect
import json
import new
import ConfigParser
import shutil

from os.path import join, exists, abspath
from shutil import copytree, ignore_patterns
from scrapy.utils.template import render_templatefile, string_camelcase

import sciscrapy
from sciscrapy.classifier import LogisticClassifier

TEMPLATES_PATH = join(sciscrapy.__path__[0], 'templates')
CLASSIFIERS_PATH = os.getcwd() + os.sep + "data"

TEMPLATES_TO_RENDER = (
    ('${classifier_name}', 'datafeatures.py.tmpl'),
)

IGNORE = ignore_patterns('*.pyc', '.svn')

class Manager(object):
    
    
    def __init__(self):
        #Find item
        f, filename, description = imp.find_module("items",)
        module = imp.load_module("items", f, filename, description)
        x = filter(lambda a: a.find("scrapy.Item") > 0, f.readlines())
        item_class_name = x[0].split("(")[0].split(" ")[1]
        print "Detected item class " + item_class_name
        self.item_class = [item[1] for item in inspect.getmembers(module, predicate=inspect.isclass) if item[0].find(item_class_name)== 0][0]
        data_dir = os.listdir(os.curdir + "/data")
        self.classifiers = {d:{}  for d in data_dir if isdir(join("data",d))} #initialize all classifiers in dictionary form
        ready=False
        for classifier in self.classifiers.keys():
            reviewed_files = glob("data/{0}/{1}".format(classifier, "/[a-z]*[0-9]*.json"))
            unreviewed_files = [f for f in glob("data/{0}/{1}".format(classifier,"/[a-z]*.json")) if reviewed_files.count(f) == 0]
            feature_extractor = glob("data/{0}/{1}".format(classifier,"/*[Ff]eature*.py"))
            settings = glob("data/{0}/{1}".format(classifier, "settings.cfg"))
            self.classifiers[classifier]["info"] = {"reviewed": len(reviewed_files), "unreviewed" : len(unreviewed_files), 
            "settings" : len(settings) == 1, "features" : len(feature_extractor)==1}
            self.classifiers[classifier]['reviewed'] = reviewed_files
            self.classifiers[classifier]['unreviewed'] = unreviewed_files
            if len(settings)==1:
                self.classifiers[classifier]['settings'] = settings[0]
            if len(reviewed_files) == 0 and len(unreviewed_files) == 0:
                print "Classifier in {0} has no data".format(classifier)
            elif len(feature_extractor) != 1:
                print "Classifier in {0} does not have a clear features file".format(classifier)
            else:
                ready = True
                fe_name = feature_extractor[0].split("/")[-1].split(".")[0]
                print fe_name
                f, filename, description = imp.find_module(fe_name, ["data"+os.sep+classifier])
                module = imp.load_module("data" + "." + classifier, f, filename, description)
                classifier_features = [extractor[1] for extractor in inspect.getmembers(module, predicate=inspect.isclass) if extractor[0].find(fe_name)== 0][0]
                self.classifiers[classifier]["features"] = classifier_features
        
        if ready == False:
            s = raw_input("Please fix the above problems before attempting to run again\nPress any key to continue...")
            sys.exit(3)
        self.main_menu()
        
    
    def program_status(self): #prints settings
        print "PROGRAM STATUS:\nCurrent Classifiers \t Reviewed \t Unreviewed \t Features\n"
        for classifier in self.classifiers.keys():
            print classifier + "\n\t\t\t {reviewed} \t\t {unreviewed} \t\t {features}\n".format(**self.classifiers[classifier]["info"]) 

    def classifier_status(self, classifier_name):
        print "                   \t Reviewed \t Unreviewed \t Features\n\t\t\t {reviewed} \t\t {unreviewed} \t\t {features}\n".format(**self.classifiers[classifier_name]["info"]) 
        if self.classifiers[classifier_name]['info']['settings']:
            config = ConfigParser.RawConfigParser()
            config.read(self.classifiers[classifier_name]['settings'])
            print "Current settngs for {0}\n Classification \t Keep".format(classifier_name)
            for classification in config.get("Classifier", "classes").split(","):
                print "{0} \t\t {1}".format(classification, config.get("Classifier", classification))
                
    def make_classifier_settings(self, classifier_name):
        config = ConfigParser.RawConfigParser()
        self.classifier_status(classifier_name)
        cont_work = True
        prompt = "0. Create new settings file\n1. Return to classifier menu"
        choice = int(raw_input(prompt))        
        while cont_work:
            if choice == 0:
                config = ConfigParser.RawConfigParser()
                names = ["none"]
                if self.classifiers[classifier_name]['info']['unreviewed']:
                    files = [re.findall('[a-z]*', s) for s in self.classifiers[classifier_name]['unreviewed']]
                    names = [item for sublist in files for item in sublist if len(re.findall("json|data|" +classifier_name, item))==0]
                print "Detected possible names " + " ".join(names)
                config.add_section("Classifier")
                classifications = raw_input("Please input classifications separated by commas\n").split(",")
                config.set("Classifier", "classes", ",".join(sorted(c.strip() for c in classifications)))
                for class_type in config.get("Classifier", "classes").split(","):
                    keep = int(raw_input("Collect data classified as {0}?\n1. Yes\n 2. No".format(class_type)))
                    if keep == 1: 
                        config.set("Classifier", class_type, True)
                    else:
                        config.set("Classifier", class_type, False)
                with open("data/{0}/settings.cfg".format(classifier_name), "wb") as configfile:                
                    config.write(configfile)
                    self.classifiers[classifier_name]['info']['settings'] = True
                    self.classifiers[classifier_name]['settings'] = configfile
                choice = 1
            elif choice == 1:
                cont_work = False
    
    def test_classifier(self, classifier_name):
        config = ConfigParser.RawConfigParser()
        config.read(self.classifiers[classifier_name]['settings'])
        classifications = config.get("Classifier", "classes").split(",")
        self.classifier_status(classifier_name)
        unreviewed_possible = True
        reviewed_possible = True
        data = {c : {} for c in classifications}
        for classification in classifications:
            
            reviewed = [f for f in self.classifiers[classifier_name]['reviewed'] if f.find(classification) >= 0]
            
            unreviewed = [f for f in self.classifiers[classifier_name]['unreviewed'] if f.find(classification) >= 0]
            data[classification]["reviewed"]=reviewed
            data[classification]["unreviewed"]=unreviewed
            if len(reviewed) == 0: reviewed_possible = False
            if len(unreviewed) == 0: unreviewed_possible = False
        prompt = "Possible options:\n"
        if unreviewed_possible: prompt+= "0. Train and test on unreviewed data\n"
        if reviewed_possible: prompt+= "1. Train and test on reviewed data\n"
        prompt += "2. Return to classifier menu\n\n"
        cont_work = True
        while cont_work:
            choice = int(raw_input(prompt))
            if choice== 0 and unreviewed_possible:
                tests = int(raw_input("Please input number of desired test trials"))
                classifier_data = []
                for classification in data.keys():
                    for f in data[classification]['unreviewed']:
                        json_file = open(f, "r")
                        json_dics = json.loads("".join(json_file.readlines()))
                        classifier_data += [(json_dic, classification) for json_dic in json_dics]
                lc = LogisticClassifier(self.classifiers[classifier_name]['features'], classifier_data, data.keys())
                print "Average accuracy over {0} iterations ".format(tests) + str(lc.estimate_accuracy(tests))
            elif choice== 1 and reviewed_possible:
                tests = int(raw_input("Please input number of desired test trials"))
                classifier_data = []
                for classification in data.keys():
                    for f in data[classification]['reviewed']:
                        try: 
                            json_file = open(f, "r")
                            json_dic = json.loads("".join(json_file.readlines()))
                            classifier_data += [(json_dic, classification)]
                        except:
                            print "Error reading ", f
                lc = LogisticClassifier(self.classifiers[classifier_name]['features'], classifier_data, data.keys())
                print "Average accuracy over {0} iterations ".format(tests) + str(lc.estimate_accuracy(tests))
            elif choice == 2:
                cont_work = False
                
    
    def review_file(self, classifier_names, data_set, i_no = 0):
        classifications_dic = defaultdict(dict)
        all_classifications = []
        for classifier_name in classifier_names:
            if self.classifiers[classifier_name]['info']['settings']:
                config = ConfigParser.RawConfigParser()
                config.read(self.classifiers[classifier_name]['settings'])
                classifications = config.get("Classifier", "classes").split(",")
                classifications_dic[classifier_name]['classifications'] = []
                for classification in classifications:
                    classifications_dic[classifier_name]['classifications'].append(classification)
                    all_classifications.append(classification)
        no_files = {}
        for classifier in classifications_dic.keys():
            reviewed = self.classifiers[classifier]['reviewed']
            for classification in list(classifications_dic[classifier]['classifications']):
                no_files[classification] = len([x for x in reviewed if x.find(classification) >= 0])
        with open(data_set, "r") as json_file:
            json_string = "".join("".join(json_file.readlines()).split("\n"))
            items = json.loads(json_string)
        for n, item in enumerate(items):
            if n > i_no-1:
                print "ITEM {0}/{1}".format(n+1, len(items))
                self.item_class.review(item)
                for classifier in classifications_dic.keys():
                    print no_files                    
                    is_a_choice = False    
                    while is_a_choice == False:
                        prompt= "Pick classification\n"
                        choices = {}
                        i = 0               
                        for classification in classifications_dic[classifier]['classifications']:
                            i+=1
                            choices[i] = classification
                            prompt+= "{0}. {1}\n".format(i, classification)
                        choice = int(raw_input(prompt))
                        if choices.has_key(choice): is_a_choice = True
                    no_files[choices[choice]]+=1
                    with open("data/{0}/{1}0{2}.json".format(classifier, choices[choice], no_files[choices[choice]]), "wb") as new_f:
                        new_f.write(json.dumps(item))
                if n+1 == len(items): self.main_menu()
                
        
    
    
    def review_classifier_data(self, classifier_name):
        self.classifier_status(classifier_name)
        choices = {}
        prompt = "What would you like to do?\n"
        for i, data_set in enumerate(self.classifiers[classifier_name]['unreviewed']):
            prompt += '{0}. Classify data in: "{1}"\n'.format(i, data_set)
            choices[i] = data_set
        prompt += '{0}. Quit\n'.format(i+1)
        choice = int(raw_input(prompt))
        cont_work = True
        while cont_work:        
            if choice < len(self.classifiers.keys()):
                self.review_file([classifier_name], choices[choice])
            elif choice == i+1:
                cont_work = False
    
    def review_classifiers_data(self, classifier_names):
        choices = {}
        prompt = "What would you like to do?\n"
        i = 0
        for classifier in classifier_names:
            if self.classifiers[classifier]['info']['unreviewed'] > 0:
                for data_set in self.classifiers[classifier]["unreviewed"]:
                    prompt += '{0}. Classify data in: "{1}"\n'.format(i, data_set)
                    choices[i] = data_set
                    i+= 1
        prompt += "{0}. Continue review of a file at a position\n".format(i+1)
        prompt += '{0}. Quit\n'.format(i+2)
        choice = int(raw_input(prompt))
        cont_work = True
        while cont_work:        
            if choice <= i:
                self.review_file(classifier_names, choices[choice])
            elif choice == i+1:
                dchoice = int(raw_input("Input number of file from above"))
                fchoice = int(raw_input("Input item number to resume review at"))
                self.review_file(classifier_names, choices[dchoice], fchoice)
            elif choice == i+2:
                cont_work = False
    
    
    def classifier_menu(self, classifier_name):
        cont_work = True
        settings = self.classifiers[classifier_name]['info']['settings']
        while cont_work:
            if settings == False: print "You MUST add a settings file to continue"
            prompt = "0. Create settings file\n1. Review {0} unreviewed data files\n2. Test classifier\n3. Return to main menu".format(self.classifiers[classifier_name]['info']['unreviewed'])
            choice = int(raw_input(prompt))
            if choice==0:
                self.make_classifier_settings(classifier_name)
            elif choice == 1 and settings:
                self.review_classifier_data(classifier_name)
            elif choice == 2 and settings:
                self.test_classifier(classifier_name)
            elif choice == 3:
                cont_work = False
    
    def create_classifier(self):
        cont_menu = True
        while cont_menu:
            classifier_name = raw_input("Please input the name for the classifier").lower().strip()
            if not re.search(r'^[_a-zA-Z]\w*$', classifier_name):
                print 'Error: Classifier names must begin with a letter and contain only\n' \
                    'letters, numbers and underscores'
            elif exists(os.getcwd() + os.sep + "data" +os.sep + classifier_name):
                print "Error: {0} already exists".format(classifier_name)
            else:
                cont_menu = False
        moduletpl = join(TEMPLATES_PATH, 'classifier')
        copytree(moduletpl, join(CLASSIFIERS_PATH, classifier_name), ignore=IGNORE)
        for paths in TEMPLATES_TO_RENDER:
            path = join(*paths)
            tplfile = join(CLASSIFIERS_PATH,
                string.Template(path).substitute(classifier_name=classifier_name))
            print tplfile
            render_templatefile(tplfile, classifier_name=classifier_name,
                ClassifierName=string_camelcase(classifier_name))
        self.classifiers[classifier_name] = {}
        self.classifiers[classifier_name]['info'] = {"reviewed": 0, "unreviewed" : 0, 
            "settings" : 0, "features" : False}
        self.make_classifier_settings(classifier_name)
        
    def main_menu(self):
        cont_prog = 1
        #Main menu
        while cont_prog == 1:
            self.program_status()
            choice = -1
            choices = {}
            prompt = "What would you like to do?\n"
            for i, classifier in enumerate(self.classifiers.keys()):
                prompt += '{0}. Work with classifier: "{1}"\n'.format(i, classifier)
                choices[i] = classifier
            prompt += '{0}. Classify unreviewed data with all classifiers\n'.format(i+1)
            prompt += '{0}. Create new classifier\n'.format(i+2)    
            prompt += '{0}. Quit\n'.format(i+3)
            choice = int(raw_input(prompt))
            if choice < len(self.classifiers.keys()):
                self.classifier_menu(choices[choice])
                cont_generate = 1
            elif choice == i+1:
                self.review_classifiers_data(self.classifiers.keys())
                cont_prog = 1
            elif choice == i+2:
                self.create_classifier()
            elif choice == i+3:
                sys.exit(0)
            
if __name__ == '__main__':
    Manager()
