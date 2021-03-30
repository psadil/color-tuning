library(hdf5r)

f <- H5File$new("data.hdf5", mode="r")

f[["class_table_mapping"]][]

data_collection <- f[["data_collection"]]

condition_variables <- data_collection[["condition_variables"]]
EXP_CV_1 <- condition_variables[["EXP_CV_1"]][]
EXP_CV_1

events <- data_collection[["events"]]

keyboard <- events[["keyboard"]][["KeyboardInputEvent"]][]
