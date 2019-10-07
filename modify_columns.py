import pandas as pd
import os

def columns_count(f_name):
    """
    Counts min/max number of columns for files
    """

    x = []
    with open(f_name, 'r') as f:
        for line in f:
            x.append(len(line.split("\t")))
    return (min(x), max(x))


def add_columns(f_name):
    """
    Add one/two columns to existing file
    """

    file_type = f_name.split(".")[-2]
    dataset_instance = f_name.split(os.path.sep)[-2]
    # print(dataset_instance)
    control_construct_scheme = dataset_instance + "_ccs01"
    # print(control_construct_scheme)

    if file_type == "dv":
        df = pd.read_csv(f_name, sep="\t", header=None, names = ["variable_name_1", "variable_name_2"])
        # print(df.head(2))
        df["dataset_instance_1"] = dataset_instance
        df["dataset_instance_2"] = dataset_instance
        cols = ["dataset_instance_1", "variable_name_1", "dataset_instance_2", "variable_name_2"]
        df = df[cols]
        # print(df.head(2))
        # overwrite
        df.to_csv(f_name, sep="\t", index=None, header=False)
    elif file_type == "qvmapping":
        df = pd.read_csv(f_name, sep="\t", header=None, names = ["question_construct", "variable_name"])
        df["control_construct_scheme"] = control_construct_scheme
        df["dataset_instance"] = dataset_instance
        cols = ["control_construct_scheme", "question_construct", "dataset_instance", "variable_name"]
        df = df[cols]
        # overwrite
        df.to_csv(f_name, sep="\t", index=None, header=False)
    elif file_type == "tvlinking":
        df = pd.read_csv(f_name, sep="\t", header=None, names = ["variable_name", "concept_identify"])
        df["dataset_instance"] = dataset_instance
        cols = ["dataset_instance", "variable_name", "concept_identify"]
        df = df[cols]
        # overwrite
        df.to_csv(f_name, sep="\t", index=None, header=False)
    elif file_type == "tqlinking":
        df = pd.read_csv(f_name, sep="\t", header=None, names = ["question_construct", "concept_identify"])
        df["control_construct_scheme"] = control_construct_scheme
        cols = ["control_construct_scheme", "question_construct", "concept_identify"]
        df = df[cols]
        # overwrite
        df.to_csv(f_name, sep="\t", index=None, header=False)
    else:
        raise NameError("should not happen")

def main():

    note_out = open("notes.txt", "w") 

    rootdir = "../bundles"
    interested = ["dv", "qvmapping", "tqlinking", "tvlinking"]

    # loops over all subdirectories of a given rootdir, if it is one of above file types, then calculate number of columns
    #for (dir, subdir, files) in os.walk(rootdir):
    for subdir in os.listdir(rootdir):
        path = os.path.join(rootdir, subdir)
        try:
            files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            print((subdir,path,files))
        except WindowsError:
            continue

        for filename in files:
            #print(filename)
            if any(x in filename for x in interested):
                file_path = os.path.join(rootdir, subdir, filename)
                #print(file_path)
                file_type = filename.split(".")[-2]
                #print(file_type)

                (min_num_columns, max_num_columns) = columns_count(file_path)
                if min_num_columns != max_num_columns:
                    note_out.write(file_path + ",number of columns are not consistent\n")
                    continue

                if file_type in ("dv", "qvmapping"):
                    if min_num_columns == 2:
                        # modify to 4 columns
                        add_columns(file_path)
                        note_out.write(file_path + ",fixed to 4 columns\n")
                    elif min_num_columns == 4:
                        note_out.write(file_path + ",already correct\n")
                    else:
                        note_out.write(file_path + ", neither 2 nor 4 columns: what to do?\n")

                elif file_type in ("tqlinking", "tvlinking"):
                    if min_num_columns == 2:
                        # modify to 3 columns
                        add_columns(file_path)
                        note_out.write(file_path + ",fixed to 3 columns\n")
                    elif min_num_columns == 3:
                        note_out.write(file_path + ",already correct\n")
                    else:
                        note_out.write(file_path + ", neither 2 nor 3 columns: what to do?\n")
                else:
                    note_out.write(file_path + ", Should not happen\n")

    note_out.close()


if __name__ == '__main__':
    main()

