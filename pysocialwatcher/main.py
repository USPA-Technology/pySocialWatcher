# -*- coding: utf-8 -*-
import sys


from utils import *
class PySocialWatcher:

    @staticmethod
    def load_credentials_file(token_file_path):
        with open(token_file_path, "r") as token_file:
            for line in token_file:
                token = line.split(",")[0].strip()
                account_number = line.split(",")[1].strip()
                PySocialWatcher.add_token_and_account_number(token, account_number)

    @staticmethod
    def add_token_and_account_number(token,account_number):
        constants.TOKENS.append((token,account_number))

    @staticmethod
    def get_behavior_dataframe():
        request_payload = {
            'type': 'adTargetingCategory',
            'class': "behaviors",
            'access_token': get_token_and_account_number_or_wait()[0]
        }
        response = send_request(constants.GRAPH_SEARCH_URL, request_payload)
        json_response = load_json_data_from_response(response)
        behaviors = pd.DataFrame()
        for entry in json_response["data"]:
            behaviors = behaviors.append({
                "behavior_id": str(entry["id"]),
                "name": entry["name"],
                "description": entry["description"],
                "audience": entry["audience_size"],
                "path": entry["path"]
            }, ignore_index=True)
        return behaviors

    @staticmethod
    def get_interests_given_query(interest_query):
        request_payload = {
            'type': 'adinterest',
            'q': interest_query,
            'access_token': get_token_and_account_number_or_wait()[0]
        }
        response = send_request(constants.GRAPH_SEARCH_URL, request_payload)
        json_response = load_json_data_from_response(response)
        interests = pd.DataFrame()
        for entry in json_response["data"]:
            interests = interests.append({
                "interest_id": str(entry["id"]),
                "name": entry["name"],
                "audience": entry["audience_size"],
                "path": entry["path"]
            }, ignore_index=True)
        return interests

    @staticmethod
    def print_interests_given_query(interest_query):
        interests = PySocialWatcher.get_interests_given_query(interest_query)
        print_dataframe(interests)

    @staticmethod
    def print_behaviors_list():
        behaviors = PySocialWatcher.get_behavior_dataframe()
        print_dataframe(behaviors)

    @staticmethod
    def read_json_file(file_path):
        file_ptr = open(file_path, "r")
        json_file_raw = file_ptr.read()
        file_ptr.close()
        try:
            json_data = json.loads(json_file_raw)
        except ValueError as error:
            raise JsonFormatException(error.message)
        return json_data

    @staticmethod
    def build_collection_dataframe(input_data_json):
        print_info("Building Collection Dataframe")
        collection_dataframe = build_initial_collection_dataframe()
        collection_queries = []
        input_combinations = get_all_combinations_from_input(input_data_json)
        print_info("Total API Requests:" + str(len(input_combinations)))
        for index,combination in enumerate(input_combinations):
            print_info("Completed: {0:.2f}".format(100*index/float(len(input_combinations))))
            collection_queries.append(generate_collection_request_from_combination(combination, input_data_json[constants.INPUT_NAME_FIELD]))
        dataframe = collection_dataframe.append(collection_queries)
        if constants.SAVE_EMPTY:
            dataframe.to_csv(constants.DATAFRAME_SKELETON_FILE_NAME)
        return dataframe

    @staticmethod
    def perform_collection_data_on_facebook(collection_dataframe):
        # Call each requests builded
        processed_rows_after_saved = 0
        dataframe_with_uncompleted_requests = collection_dataframe[pd.isnull(collection_dataframe["response"])]
        while not dataframe_with_uncompleted_requests.empty:
            print_collecting_progress(dataframe_with_uncompleted_requests, collection_dataframe)
            # Trigger requests
            rows_to_request = dataframe_with_uncompleted_requests.head(len(constants.TOKENS))
            responses_list = trigger_request_process_and_return_response(rows_to_request)
            # Save response in collection_dataframe
            save_response_in_dataframe(responses_list, collection_dataframe)
            processed_rows_after_saved += len(responses_list)
            # Save a temporary file
            if processed_rows_after_saved >= constants.SAVE_EVERY:
                save_temporary_dataframe(collection_dataframe)
                processed_rows_after_saved = 0
            # Update not_completed_experiments
            dataframe_with_uncompleted_requests = collection_dataframe[pd.isnull(collection_dataframe["response"])]
        print_info("Data Collection Complete")
        save_temporary_dataframe(collection_dataframe)
        post_process_collection(collection_dataframe)
        save_after_collecting_dataframe(collection_dataframe)
        return collection_dataframe

    @staticmethod
    def check_input_integrity(input_data_json):
        # Languages should have just 'or' key
        pass

    @staticmethod
    def run_data_collection(json_input_file_path):
        input_data_json = PySocialWatcher.read_json_file(json_input_file_path)
        PySocialWatcher.check_input_integrity(input_data_json)
        collection_dataframe = PySocialWatcher.build_collection_dataframe(input_data_json)
        save_temporary_dataframe(collection_dataframe)
        sys.exit(0)
        collection_dataframe = PySocialWatcher.perform_collection_data_on_facebook(collection_dataframe)
        return collection_dataframe

    @staticmethod
    def load_data_and_continue_collection(input_file_path):
        collection_dataframe = load_dataframe_from_file(input_file_path)
        collection_dataframe = PySocialWatcher.perform_collection_data_on_facebook(collection_dataframe)
        return  collection_dataframe

    @staticmethod
    def config(sleep_time = 8, save_every = 300, save_after_empty_dataframe = False):
        constants.SLEEP_TIME = sleep_time
        constants.SAVE_EVERY = save_every
        constants.SAVE_EMPTY = save_after_empty_dataframe

    @staticmethod
    def print_bad_joke():
        print "I used to think the brain was the most important organ.\nThen I thought, look what’s telling me that."
