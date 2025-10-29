import json

import pandas as pd

from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.net_work import GrpcClient
from fediux.utils.logger_util import logger

import os
import time
from transformers import AutoConfig, AutoTokenizer, AutoModel
import torch


class ChatGlmClient(BaseModel):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        process = self.common_params['process']
        logger.info(f"process: {process}")
        if process == 'train':
            self.train()
        elif process == 'predict':
            self.predict()
        else:
            error_msg = f"Unsupported process: {process}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def train(self):
        role_params = self.role_params

        num_examples = self.role_params['num_examples']

        #send num_sampes
        remote_party = self.roles[self.role_params['others_role']]
        self.channel = GrpcClient(local_party=self.role_params['self_name'],
                                  remote_party=remote_party,
                                  node_info=self.node_info,
                                  task_info=self.task_info)

        self.channel.send('num_examples', num_examples)

        path = role_params['path']
        os.chdir(path)
        local_epoch = self.common_params['local_epoch']
        learning_rate = self.common_params['learning_rate']
        global_epoch = self.common_params['global_epoch']
        train_file = role_params['train_file']
        validation_file = role_params['validation_file']
        prompt_column = role_params['prompt_column']
        response_column = role_params["response_column"]
        history_column = role_params[
            'history_column'] if 'history_column' in role_params else None
        model_name_or_path = role_params['model_name_or_path']
        output_dir = role_params['output_dir']
        ptuning_checkpoint = f"{output_dir}/checkpoint-{local_epoch}"

        for i in range(global_epoch):
            cmd = f"python3 main.py \
                        --do_train \
                        --train_file {train_file} \
                        --validation_file {validation_file} \
                        --prompt_column {prompt_column} \
                        --response_column {response_column} \
                        --overwrite_cache \
                        --model_name_or_path  {model_name_or_path}\
                        --output_dir {output_dir} \
                        --overwrite_output_dir \
                        --max_source_length 64 \
                        --max_target_length 64 \
                        --per_device_train_batch_size 1 \
                        --per_device_eval_batch_size 1 \
                        --gradient_accumulation_steps 1 \
                        --predict_with_generate \
                        --max_steps {local_epoch} \
                        --logging_steps 1 \
                        --save_steps {local_epoch} \
                        --learning_rate {learning_rate} \
                        --pre_seq_len 128"

            if history_column != None:
                cmd += f"  --history_column {history_column}"
            if i != 0:
                cmd += f"  --ptuning_checkpoint {ptuning_checkpoint}"
            print(f"cmd is {cmd}")
            os.system(cmd)
            time.sleep(5)  #for save
            import torch
            prefix_state_dict = torch.load(
                os.path.join(path + "/" + ptuning_checkpoint,
                             "pytorch_model.bin"))
            self.channel.send(f'client_res_{i}', prefix_state_dict)
            res = self.channel.recv(f'server_res_{i}')
            torch.save(
                res,
                os.path.join(path + "/" + ptuning_checkpoint,
                             "pytorch_model.bin"))
            if i == global_epoch - 1:
                os.makedirs(os.path.dirname(self.role_params["model_path"]), exist_ok=True)
                torch.save(res, self.role_params["model_path"])
            del torch

    def predict(self):
        import torch
        model_path = self.role_params['model_path']
        model_name_or_path = self.role_params['model_name_or_path']
        tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, trust_remote_code=True)

        config = AutoConfig.from_pretrained(model_name_or_path, trust_remote_code=True)
        config.pre_seq_len = 128
        config.prefix_projection = False

        model = AutoModel.from_pretrained(model_name_or_path, config=config, trust_remote_code=True)
        prefix_state_dict = torch.load(model_path)
        new_prefix_state_dict = {}
        for k, v in prefix_state_dict.items():
            if k.startswith("transformer.prefix_encoder."):
                new_prefix_state_dict[k[len("transformer.prefix_encoder."):]] = v
        model.transformer.prefix_encoder.load_state_dict(new_prefix_state_dict)

        model = model.float()
        model = model.eval()

        result = []
        with open(os.path.join(self.role_params["path"], self.role_params["source"]), 'r', encoding='utf-8') as f:
            for line in f.readlines():
                text = json.loads(line)["content"]
                response, history = model.chat(tokenizer, text, history=[])
                result.append([text, response])
        df = pd.DataFrame(result, columns=["content", "result"])
        os.makedirs(os.path.dirname(self.role_params["predict_path"]), exist_ok=True)
        df.to_csv(os.path.join(self.role_params["path"], self.role_params["predict_path"]), index=False)
        del torch

