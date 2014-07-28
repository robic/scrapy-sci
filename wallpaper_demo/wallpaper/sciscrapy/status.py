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



class Status(object):
    
    
    def __init__(self):

        #Find item
        self.management_ready = False
        self.crawl_ready = False
        self.item = None
        try:
            f, filename, description = imp.find_module("items",)
            module = imp.load_module("items", f, filename, description)
            x = filter(lambda a: a.find("scrapy.Item") > 0, f.readlines())
            item_class_name = x[0].split("(")[0].split(" ")[1]
            print "Detected item class " + item_class_name
            self.item = [item[1] for item in inspect.getmembers(module, predicate=inspect.isclass) if item[0].find(item_class_name)== 0][0]
            self.crawl_ready = True
        except:
            print "Unable to find item class"
    
        #Find classifiers and files
        data_dir = os.listdir(os.curdir + "/data")
        self.classifiers = {d:{}  for d in data_dir if isdir(join("data",d))} #initialize all classifiers in dictionary form
        self.classify_ready=False
        for classifier in self.classifiers.keys():
            seed_files = glob("data/{0}/{1}".format(classifier, "/[a-z]*_seed.json"))   
            reviewed_files = glob("data/{0}/{1}".format(classifier, "/[a-z]*[0-9]*.json"))
            unreviewed_files = [f for f in glob("data/{0}/{1}".format(classifier,"/[a-z]*.json")) if reviewed_files.count(f) == 0]
            settings = glob("data/{0}/{1}".format(classifier, "/settings.cfg"))
            #Find features for classifier
            feature_extractor = glob("data/{0}/{1}".format(classifier,"/*[Ff]eature*.py"))
            if len(feature_extractor) == 1:
                try:    
                    fe_name = feature_extractor[0].split("/")[-1].split(".")[0]
                    f, filename, description = imp.find_module(fe_name, ["data"+os.sep+classifier])
                    module = imp.load_module("data" + "." + classifier, f, filename, description)
                    classifier_features = [extractor[1] for extractor in inspect.getmembers(module, predicate=inspect.isclass) if extractor[0].find("FeatureExtractor")== -1][0]
                    self.classifiers[classifier]["features"] = classifier_features
                except:
                    print "Error trying to read feature extractor file; make sure the feature class is the only class in the file {0}".format(feature_extractor[0])
            else:
                print "Only one feature extractor per classifier allowed"
                
            
            self.classifiers[classifier]['seeds'] = reviewed_files
            self.classifiers[classifier]['reviewed'] = reviewed_files
            self.classifiers[classifier]['unreviewed'] = unreviewed_files
            
            if len(settings) == 1:
                self.classifiers[classifier]['classifications'] = {}
                config = ConfigParser.RawConfigParser()
                config.read([settings[0]])
                for classification in config.get("Classifier", "classes").split(","):
                    self.classifiers[classifier]['classifications'][classification] = \
                    config.get("Classifier", classification)
            #If even one classifier is ready; the program is ready for classification
            if len(settings) != 1:
                print "Classifier in {0} has no clear settings".format(classifier)
            elif len(reviewed_files) == 0 and len(unreviewed_files) == 0 and len(seed_files)==0:
                print "Classifier in {0} has no data".format(classifier)
            elif self.classifiers[classifier].has_key("features") == False:
                print "Classifier in {0} does not have a clear features file".format(classifier)
            else:
                self.classify_ready = True
                
            self.classifiers[classifier]["info"] = {"seeds": len(seed_files), \
            "reviewed": len(reviewed_files), "unreviewed" : len(unreviewed_files), 
            "settings" : len(settings) == 1, "features" : self.classify_ready}
                
    def program_status(self): #prints settings
        print "PROGRAM STATUS:\nCurrent Classifiers \t Reviewed \t Unreviewed \t Features\n"
        for classifier in self.classifiers.keys():
            print classifier + "\n\t\t\t {reviewed} \t\t {unreviewed} \t\t {features}\n".format(**self.classifiers[classifier]["info"]) 

    def classifier_status(self, classifier_name):
        print "Classifier: {0}".format(classifier_name.upper())
        print "                   \t Reviewed \t Unreviewed \t Features\n\t\t\t {reviewed} \t\t {unreviewed} \t\t {features}\n".format(**self.classifiers[classifier_name]["info"]) 
        if self.classifiers[classifier_name]['info']['settings']:
            print "Classifications :\n\tName:Keep\n".format(classifier_name)
            classifications_string = ""
            for i, classification in enumerate(self.classifiers[classifier_name]['classifications'].keys()):
                classifications_string+="{0}:{1}\t".format(classification, self.classifiers[classifier_name]\
                ['classifications'][classification])
                if i+1 % 4 == 0: classifications_string += "\n"
            print classifications_string, "\n\n"
                
                
                
                
                
                
                
                