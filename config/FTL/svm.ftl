{
	"roles": {
		"server": "Alice",
		"client": [
			"Bob",
			"Charlie"
		]
	},
	"common_params": {
		"model": "${model}",
		"method": "${encryption!"Plaintext"}",
		"process": "train",
		"task_name": "SVM_plaintext_train",
		"selected_column": ${label_field0},
		"id": "${id!"id"}",
		"label": "${label!"y"}",
		"print_metrics": ${printMetrics!false?c},
		"kernel": "${kernel!"linear"}"
	},
	"role_params": {
		"Bob": {
			"data_set": "${label_dataset}",
			"model_path": "${hostModelFileName}",
			"metric_path": "${indicatorFileName}"
		},
		"Charlie": {
			"data_set": "${guest_dataset}",
			"model_path": "${guestModelFileName}",
			"metric_path": "${indicatorFileName}"
		},
		"Alice": {
			"data_set": "${arbiter_dataset}",
			"metric_path": "/data${indicatorFileName}"
		}
	}
}