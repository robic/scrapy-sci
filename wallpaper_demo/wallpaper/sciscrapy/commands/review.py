import os
import sys
from scrapy.command import ScrapyCommand
from scrapy.utils.conf import arglist_to_dict
from scrapy.exceptions import UsageError
from collections import defaultdict
import json
from wallpaper.sciscrapy.status import Status, Reader
from wallpaper.sciscrapy.classifier import LogisticClassifier, ClassifierCreator

class Command(ScrapyCommand):

    requires_project = True
    
    def syntax(self):
        return "[options] <file_name>"

    def short_desc(self):
        return "Review file with classifiers"

    def add_options(self, parser):
        ScrapyCommand.add_options(self, parser)
        parser.add_option("-c", "--classifiers", dest="classifiers", action="append", default=[],
                          help="list classifiers by which the file will be reviewed")
        parser.add_option("-r", "--resume", dest="i_no", type="int", default=0,
                          help="resume review of a file at a given item")
    
    def process_options(self, args, opts):
        ScrapyCommand.process_options(self, args, opts)
        

    def run(self, args, opts):
        if len(args) < 1:
            raise UsageError()
        elif len(args) > 1:
            raise UsageError("running 'scrapy review' with more than one argument is not supported")
        file_name = args[0]
        status = Status()
        if len(opts.classifiers) == 0: opts.classifiers = status.classifiers.keys() #If all classifiers are to be used
        #Setting up classifiers which are possible
        valid_classifiers = defaultdict(dict)#Dictionary for currently feasible classifiers only
        for classifier_name in status.classifiers.keys():
            classifications = []
            if status.classifiers[classifier_name]['info']['settings'] and opts.classifiers.count(classifier_name) == 1:
                valid_classifiers[classifier_name]['classifications'] = \
                sorted(status.classifiers[classifier_name]['classifications'])
        #Counting files for valid classifiers
        no_files = {}
        classifiers = valid_classifiers.keys()
        for classifier in valid_classifiers.keys():
            reviewed = status.classifiers[classifier]['reviewed']
            for classification in list(valid_classifiers[classifier]['classifications']):
                no_files[classification] = len([x for x in reviewed if x.find(os.sep + classification) >= 0])
        items = Reader.read_unreviewed(file_name)
        #Confirmation mode
        confirmation_mode = False
        conf_input = 3
        while conf_input > 2:
            try:
                conf_input = int(raw_input("1. Keep the same\n2. Turn on confirmation mode"))
            except:
                print "Wrong input"
            if conf_input == 2: confirmation_mode = True
        #Review of items
        n = opts.i_no
        while n < len(items):
            print "ITEM {0}/{1}".format(n, len(items))
            print no_files
            item = items[n]
            status.item.review(item)
            if n >= opts.i_no:
                to_write = {}
                for classifier in valid_classifiers.keys():
                    #Loop to ensure a choice
                    is_a_choice = False
                    while is_a_choice == False:
                        prompt= "Pick classification\n"
                        choices = {}
                        i = 0               
                        for classification in valid_classifiers[classifier]['classifications']:
                            i+=1
                            choices[i] = classification
                            prompt+= "{0}. {1}\t".format(i, classification)
                            if i % 3 == 0: prompt += "\n"
                        try:
                            choice = int(raw_input(prompt))
                        except:
                            print "Wrong input"
                        if choices.has_key(choice): is_a_choice = True
                    to_write[classifier] = choices[choice]
                confirmed = True
                if confirmation_mode:
                    confirmed = False
                    print "Choices: {0}".format("\t".join(to_write))
                    choice = 3
                    while choice < 0 and choice > 1:
                        try:
                            choice  = int(raw_input("0. Confirm \n 1. Reclassify"))
                        except:
                            print "Wrong input"
                        if choice == 0: confirmed = True
                if confirmed:
                    for classifier in to_write.keys():
                        classifier_dir = os.path.join(status.data_dir, classifier)
                        no_files[to_write[classifier]]+=1
                        new_f_name
                        with open(os.path.join(classifier_dir, new_f_name), "wb") as new_f:
                            new_f.write(json.dumps(item))
                    n+=1
                if n == len(items): sys.exit()