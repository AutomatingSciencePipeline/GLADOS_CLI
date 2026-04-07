from core.experiment import Experiment

class MyExperiment(Experiment):
    def __init__(self):
        hyperparams = {
            #variable : (start, stop, step_size)
            
        }

        super().__init__(hyperparams,
                         csv_name="output.csv")
    

    def process_trial(self, data):
        # your defined function here
        # e.g. compute f(x, y, z)
        pass
    
    def graph_result(self, data, save_path):
        # your defined graph function here
        pass


def main():
    new_exp = MyExperiment() 
    new_exp.doExperiment()
            
if __name__ == "__main__":
    main()