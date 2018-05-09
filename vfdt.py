# vfdt class, vfdt_node class, Example class
# test in command line window
# in program directory: python3 vfdt.py
#
# Jamie
# 08/05/2018
# ver 0.01

import numpy as np
import pandas as pd
import math
import time


# tringing example class
class Example:
    def __init__(self, line):
        self.x = line[:-1]  # attributes values
        self.y = line[-1]  # label


# VFDT node class
class vfdt_node:
    # parameter nijk: statistics of feature i, value j, class k
    def __init__(self, possible_split_features):
        self.parent = None
        self.children = None
        self.split_feature = None
        self.new_examples_seen = 0
        self.total_examples_seen = 0
        self.class_frequency = {}
        self.nijk = {i:{} for i in possible_split_features}
        self.possible_split_features = possible_split_features

    def add_children(self, split_feature, nodes):
        if (not nodes):
            raise Exception('no children')
        self.split_feature = split_feature
        self.children = nodes
        self.nijk.clear()

    # recursively trace down the tree to distribute data examples to corresponding leaves
    def sort_example(self, example):
        value = 0
        if (self.children != None):
            index = self.possible_split_features.index(self.split_feature)
            value = example.x[index]
            return(self.children[value].sort_example(example))
        else:
            return(self)


    def is_leaf(self):
        return(self.children == None)

    def display_children(self):
        if (self.is_leaf()):
            print('It is leaf')
        else:
            print(list(self.children.keys()))
            for key in self.children:
                print(self.children[key].split_feature, end=' ')
            print()

    # the most frequent classification
    def most_frequent(self):
        if (not self.is_leaf()):
            raise Exception('Not a leaf')
        else:
            if (not self.class_frequency and self.parent != None):
                class_frequency = self.parent.class_frequency
                prediction = max(class_frequency, key=class_frequency.get)
            else:
                prediction = max(self.class_frequency, key=self.class_frequency.get)
            return(prediction)

    # upadate leaf stats in order to calculate infomation gain
    def update_stats(self, example):
        label = example.y
        if(self.is_leaf() == False):
            raise Exception('This is not a leaf')
        feats = self.possible_split_features
        for i in feats:
            if (i != None):
                value = example.x[feats.index(i)]
                if (value not in self.nijk[i]):

                    d = {label : 1}
                    self.nijk[i][value] = d
                else:
                    if (label not in self.nijk[i][value]):
                        self.nijk[i][value][label] = 1
                    else:
                        self.nijk[i][value][label] += 1
        self.total_examples_seen += 1
        self.new_examples_seen += 1
        if (label not in self.class_frequency):
            self.class_frequency[label] = 1
        else:
            self.class_frequency[label] += 1

    # use hoeffding tree model to test node split, return the split feature
    def splittable(self, delta, nmin):
        if(self.new_examples_seen < nmin):
            return(None)
    
        else:
            self.new_examples_seen = 0  # reset

        mx = 0
        second_mx = 0
        Xa = ''
        for feature in self.possible_split_features:
            if (feature != None):
                value = self.info_gain(feature)
                if (value > mx):
                    mx = value
                    Xa = feature
                elif (value > second_mx and value < mx):
                    second_mx = value
        R = math.log10(len(self.class_frequency))
        sigma = self.hoeffding_bound(R, delta, self.total_examples_seen)
        if (mx - second_mx > sigma):
            return(Xa)
        #elif (sigma < tau and mx - second_mx < tau):
            #return(Xa)
        else:
            return(None)

    # hoeffding bound, by Domingos & Hulten 2000
    def hoeffding_bound(self, R, delta, n):
        return(math.sqrt((R*R) * math.log(1/delta) / (2 * n)))

    def entropy(self, class_frequencies):
        total_examples = 0
        for k in class_frequencies:
            total_examples += class_frequencies[k]
        if (total_examples == 0):
            return(0)

        entropy = 0
        for k in class_frequencies:
            if(class_frequencies[k] != 0):
                entropy += -(class_frequencies[k] / float(total_examples)) * math.log2(class_frequencies[k] / float(total_examples))
            else:
                entropy += 0

        return(entropy)

    # nijk: attribute i, value j of class k
    def info_gain(self, featureID):
        njk = self.nijk[featureID]
        class_frequency = self.class_frequency

        total_examples = self.total_examples_seen
        if (total_examples == 0):
            return(0)
        entropy_before = self.entropy(class_frequency)

        # for each value j, class frequency must be counted
        entropy_after = 0
        for j in njk:
            count = 0
            for k in njk[j]:
                count += njk[j][k]
            entropy_after += (count/float(total_examples)) * (self.entropy(njk[j]))

        ig = entropy_before - entropy_after
        return ig

    def get_visualization(self, indent):
        if (self.children == None):
            return(indent + 'Leaf\n')
        else:
            visualization = ''
            for key in self.children:
                visualization += indent + self.split_feature + ' = ' + str(key) + ':\n'
                visualization += self.children[key].get_visualization(indent + ' | ')
            return(visualization)

# very fast decision tree class, i.e. hoeffding tree
class vfdt:
    # parameters
    # feature_values  # number of values of each feature # dict
    # feature_values = {feature:[unique values list]}
    # delta   # used for hoeffding bound
    # tau  # used to deal with ties
    # nmin  # used to limit the G computations

    def __init__(self, feature_values, delta, nmin):
        self.feature_values = feature_values
        self.delta = delta
        #self.tau = tau
        self.nmin = nmin
        features = list(feature_values.keys())
        self.root = vfdt_node(features)
        self.n_examples_processed = 0

    # update the tree by adding training example
    def update(self, example):
        self.n_examples_processed += 1
        node = self.root.sort_example(example)
        node.update_stats(example)

        split_feature = node.splittable(self.delta, self.nmin)
        if (split_feature != None):
            children =  self.node_split(node, split_feature)
            node.add_children(split_feature, children)
            for key in children:
                children[key].parent = node

    # split node, produce children
    def node_split(self, node, split_feature):
        features = node.possible_split_features
        # replace deleted split feature with None
        new_features = [None if f == split_feature else f for f in features]
        children = {}
        for v in self.feature_values[split_feature]:
            children[v] = vfdt_node(new_features)
        return(children)

    # predict test example's classification
    def predict(self, example):
        node = self.root.sort_example(example)
        prediction = node.most_frequent()
        return(prediction)

    # accuracy of a test set
    def accuracy(self, examples):
        correct = 0
        for ex in examples:
            if (self.predict(ex) == ex.y):
                correct +=1
        return(float(correct) / len(examples))


def main():
    start_time = time.time()

    # bank.csv whole data size: 4521
    # if more than 4521, it revert back to 4521
    rows = 1000
    n_training = int(0.8 * rows)
    # read_csv has parameter nrows=n that read the first n rows
    df = pd.read_csv('bank.csv', nrows=rows, header=0, sep=";")
    title = list(df.columns.values)
    features = title[:-1]
    # need to pre-process data before training, discretize continous data
    # unique values for each feature to use in VFDT
    feature_values = {f:None for f in features}
    bins = 0
    for f in features:
        if (df[f].dtype != np.float64 and df[f].dtype != np.int64):
            feature_values[f] = df[f].unique()
            temp = len(feature_values[f])
            if (temp > bins):
                bins = temp
    # bins for discretization
    # set bins to maximum unique values of discrete features
    # could use different method, then set labels equals to bins
    labels = [i for i in range(1, bins+1)]  # labels to replace bins

    for f in features:
        if (df[f].dtype == np.float64 or df[f].dtype == np.int64):
            # check if feature value is continous
            # pd.cut to discretize continous feature values in same size bins.
            # pd.qcut put same number of data in each bin
            # But it doesn't work here because not enough values in each bin.
            df[f] = pd.cut(df[f], bins, labels=labels)
            feature_values[f] = df[f].unique()

    # convert df to data examples
    array = df.head(n_training).values
    examples = []
    possible_split_features = title[:-1]
    n = len(array)
    for i in range(n):
        ex = Example(array[i])
        examples.append(ex)

    # heoffding bound parameter delta: with 1 - delta probability
    # the true mean is at least r - gamma
    # vfdt parameter nmin: test split if new sample size > nmin
    delta = 0.01
    nmin = 10
    tree = vfdt(feature_values, delta, nmin)
    for ex in examples:
        tree.update(ex)
    # print(tree.root.get_visualization('$'))

    # test set is different from training set
    n_test = rows - n_training
    test_set = df.tail(n_test).values
    test = []
    for i in range(len(test_set)):
        sample = Example(test_set[i])
        test.append(sample)

    print('Total data size: ', rows)
    print('Training set: ', len(array))
    print('Test set: ', len(test_set))
    print('ACCURACY: %.4f' % tree.accuracy(test))

    print("--- Running time: %.6f seconds ---" % (time.time() - start_time))

if __name__ == "__main__":
    main()