# ScenariosCreator.py - Class to create and deliver scenarios using parmest
# DLW March 2020

import json
import pyomo.contrib.parmest.parmest as parmest
import pyomo.environ as pyo


class ScenarioSet(object):
    """
    Class to hold scenario sets
    Args:
    name (str): name of the set (might be "")
    NOTE: Delete this note by May 2020
         As of March 2020, this uses a list as the underlying data structure.
         The list could be changed to a dataframe with not outside impact.
    """

    def __init__(self, name):
        self.scens = list()  # use a df instead?
        self.name = name  #  might be ""

    def addone(self, scen):
        """ Add a scenario to the set
        Args:
            scen (_ParmestScen): the scenario to add
        """
        assert(isinstance(self.scens, list))
        self.scens.append(scen)

    def Concatwith(self, set1,  newname):
        """ Concatenate a set to this set and return a new set 
        Args: 
            set1 (ScenarioSet): to append to this
        Returns:
            a new ScenarioSet
        """
        assert(isinstance(self.scens, list))
        newlist = self.scens + set1.scens
        retval = ScenarioSet(newname)
        retval.scens = newlist
        return retval


    def append_bootstrap(self, bootstrap_theta):
        """ Append a boostrap theta df to the scenario set; equally likely
        Args:
            boostrap_theta (dataframe): created by the bootstrap
        Note: this can be cleaned up a lot with the list becomes a df,
              which is why I put it in the ScenarioSet class.
        """
        assert(len(bootstrap_theta > 0))
        prob = 1. / len(bootstrap_theta)

        # dict of ThetaVal dicts
        dfdict = bootstrap_theta.to_dict(orient='index')

        for index, ThetaVals in dfdict.items():
            name = "Boostrap"+str(index)
            self.addone(_ParmestScen(name, ThetaVals, prob))


    def write_csv(self, filename):
        """ write a csv file with the scenarios in the set
        Args:
            filename (str): full path and full name of file
        """
        if len(self.scens) == 0:
            print ("Empty scenario set, not writing file={}".format(filename))
            return
        with open(filename, "w") as f:
            f.write("Name,Probability")
            for n in self.scens[0].ThetaVals.keys():
                f.write(",{}".format(n))
            f.write('\n')
            for s in self.scens:
                f.write("{},{}".format(s.name, s.probability))
                for v in s.ThetaVals.values():
                    f.write(",{}".format(v))
                f.write('\n')


class _ParmestScen(object):
    # private class to hold scenarios

    def __init__(self, name, ThetaVals, probability):
        # ThetaVals is a dict: ThetaVals[name]=val
        self.name = name  # might be ""
        assert(isinstance(ThetaVals, dict))
        self.ThetaVals = ThetaVals
        self.probability = probability

############################################################


class ScenarioCreator(object):
    """ Create scenarios from parmest.

    Args:
        pest (Estimator): the parmest object
        solvername (str): name of the solver (e.g. "ipopt")

    """

    def __init__(self, pest, solvername):
        self.pest = pest
        self.solvername = solvername
        self.experiment_numbers = pest._numbers_list


    def ScenariosFromExperiments(self, addtoSet):
        """Creates new self.Scenarios list using the experiments only.
        Args:
            addtoSet (ScenarioSet): the scenarios will be added to this set
        Returns:
            a ScenarioSet
        """

        assert(isinstance(addtoSet, ScenarioSet))
        prob = 1. / len(self.pest._numbers_list)
        for exp_num in self.pest._numbers_list:
            print("Experiment number=", exp_num)
            model = self.pest._instance_creation_callback(exp_num,
                                                        self.pest.callback_data)
            opt = pyo.SolverFactory(self.solvername)
            results = opt.solve(model)  # solves and updates model
            ## pyo.check_termination_optimal(results)
            ThetaVals = dict()
            for theta in self.pest.theta_names:
                tvar = eval('model.'+theta)
                tval = pyo.value(tvar)
                print("    theta, tval=", tvar, tval)
                ThetaVals[theta] = tval
            addtoSet.addone(_ParmestScen("ExpScen"+str(exp_num), ThetaVals, prob))
            
    def ScenariosFromBoostrap(self, addtoSet, numtomake):
        """Creates new self.Scenarios list using the experiments only.
        Args:
            addtoSet (ScenarioSet): the scenarios will be added to this set
            numtomake (int) : number of scenarios to create
        """

        assert(isinstance(addtoSet, ScenarioSet))

        bootstrap_thetas = self.pest.theta_est_bootstrap(numtomake)
        addtoSet.append_bootstrap(bootstrap_thetas)

        
if __name__ == "__main__":
    # quick test using semibatch
    import pyomo.contrib.parmest.examples.semibatch.semibatch as sb

    # Vars to estimate in parmest
    theta_names = ['k1', 'k2', 'E1', 'E2']

    # Data, list of dictionaries
    data = [] 
    for exp_num in range(10):
        fname = 'examples/semibatch/exp'+str(exp_num+1)+'.out'
        with open(fname,'r') as infile:
            d = json.load(infile)
            data.append(d)

    # Note, the model already includes a 'SecondStageCost' expression 
    # for sum of squared error that will be used in parameter estimation

    pest = parmest.Estimator(sb.generate_model, data, theta_names)
    
    scenmaker = ScenarioCreator(pest, "ipopt")

    ####experimentscens = ScenarioSet("Experiments")
    ####scenmaker.ScenariosFromExperiments(experimentscens)
    ####experimentscens.write_csv("delme_exp_csv.csv")

    bootscens = ScenarioSet("Bootstrap")
    numtomake = 3
    scenmaker.ScenariosFromBoostrap(bootscens, numtomake)
    
    bootscens.write_csv("delme_boot_csv.csv")
