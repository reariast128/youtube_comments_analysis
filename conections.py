import os
import googleapiclient.discovery
import requests
from transformers import pipeline
from tqdm import tqdm
import json
from utils import ReadApiKeys

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

class ApiHandle:
    '''ApiHandle contains necesary functions to connnect with YouTube and Hugging Face API.
    which are used in analysis functions in this exercise.
    
    YOUTUBE_API_KEY: YouTube API key.
    '''

    def __init__(self, YOUTUBE_API_KEY: str) -> None:
        self.YOUTUBE_API_KEY = YOUTUBE_API_KEY
    
    def get_sentiment_from_text(self, text: str) -> str:
        '''Uses lxyuan/distilbert-base-multilingual-cased-sentiments-student to get the perception of a text. This can be ``positive``, ``neutral`` or ``negative``
        Returns the label of the text's principal sentiment.'''

        # build the pipeline
        model = pipeline(
            model="lxyuan/distilbert-base-multilingual-cased-sentiments-student", 
            top_k=1
        )

        # pass the text to the model to get a response
        response = model(text)

        # return the label of the top 1 sentiment
        return response[0][0]['label']

    def fetch_youtube_video_comments(self, video_ID: str, page_token: str = '') -> dict:
        '''Get the comments JSON of a YouTube video using googleapiclient.
        `page_token` is an optional argument, that indicates to request to fetch only a comments page from the whole comments avaiable in the video.
        '''

        # build the youtube conection
        youtube_conection = googleapiclient.discovery.build(
            'youtube', 'v3', developerKey = self.YOUTUBE_API_KEY)
        
        request = youtube_conection.commentThreads().list(
                part="snippet,replies",
                videoId=video_ID,
                maxResults=100,
                pageToken=page_token
            ) # type: ignore
            
        # trying request and handling with possible errors
        try:
            response = request.execute() # type: ignore
            if 'error' in response.keys():
                raise
            else:
                print(f"Request id {response['etag']} was executed sucessfully.")
                return response
            
        except googleapiclient.discovery.HttpError as error:
            error_reason = error.reason
            print(f"Error in YouTube connection.")
            print(f"Reason: {error_reason}")
            raise

    def fetch_youtube_video_info(self, video_ID: str) -> dict:
        '''Get the JSON with the video info by a HTTPS request.'''
        request_url = f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet%2CcontentDetails%2Cstatistics&id={video_ID}&key={self.YOUTUBE_API_KEY}"
        try:
            response = requests.get(request_url)
            if response.status_code == 200:
                return response.json()
            else:
                raise
        except requests.HTTPError as error:
            print(error.response)
            raise

    def fetch_all_youtube_video_comments(self, video_ID: str) -> list:
        '''Retrieves a JSON with all the comments page from a video.'''
        responses = []
        try:
            print(f"Trying to get all comments from {video_ID} video.")
            response = self.fetch_youtube_video_comments(video_ID)
            responses.append(response)

            while 'nextPageToken' in response.keys():
                next_page_token = response['nextPageToken']
                response = self.fetch_youtube_video_comments(video_ID, page_token=next_page_token)
                responses.append(response)

            return responses
        
        except googleapiclient.discovery.HttpError as error:
            error_reason = error.error_details
            print(f"Error in YouTube connection.")
            print(f"Reason: {error_reason}")
            raise 

    def extract_comment_text_and_date(self, youtube_response_json: list) -> list[dict]:
            '''Returns a json-like list with relevant data of the YouTube's response list.
            Returns a list like this:
                [
                    {
                        'text': comment['snippet']['topLevelComment']['snippet']['textDisplay'],
                        'date': comment['snippet']['topLevelComment']['snippet']['updatedAt']
                    },
                    ...
                ]
            response_list: List with YouTube's response.'''

            comments = []
            for response in youtube_response_json:
                for comment in response['items']:
                    data = {
                        'text': comment['snippet']['topLevelComment']['snippet']['textDisplay'],
                        'date': comment['snippet']['topLevelComment']['snippet']['updatedAt']
                    }
                    comments.append(data)

            return comments
    
class AnalysisHandle():

    def __init__(self, YOUTUBE_API_KEY: str):
        self.handler = ApiHandle(YOUTUBE_API_KEY)
    
    def fetch_youtube_video_comments_with_sentiments(self, video_id: str) -> list[dict]:
        '''Get all comments from the `video_id` video, returning a dict like this:
        [
            {
                'text': comment['snippet']['topLevelComment']['snippet']['textDisplay'],
                'date': comment['snippet']['topLevelComment']['snippet']['updatedAt'],
                'emotion': get_sentiment_from_text(list[comment_index]['text'])
            },
            ...
        ]'''
        
        video_youtube_comments_json = self.handler.fetch_all_youtube_video_comments(video_id)
        video_youtube_comments_json = self.handler.extract_comment_text_and_date(video_youtube_comments_json)

        # checking if video_youtube_comments_json has more than 10000 comments and raises a warning
        if len(video_youtube_comments_json) > 10000:
            print("WARNING: video_youtube_comments_json has more than 10000 records. The first 10000 records will be parsed.")
            video_youtube_comments_json = video_youtube_comments_json[:10000]

        # trying to get all comments sentiment
        print("Trying to get all comments sentiment")
        for comment in tqdm(range(0, len(video_youtube_comments_json))):
            if len(video_youtube_comments_json[comment]['text']) > 511:
                continue
            else:
                video_youtube_comments_json[comment]['sentiment'] = self.handler.get_sentiment_from_text(video_youtube_comments_json[comment]['text'])

        return video_youtube_comments_json
    
    def fetch_video_info_and_stats(self, video_id: str) -> dict:
        response = self.handler.fetch_youtube_video_info(video_id)

        video_info = {
            'thumbnail_url': response['items'][0]['snippet']['thumbnails']['high']['url'],
            'video_title': response['items'][0]['snippet']['title'],
            'channel_name': response['items'][0]['snippet']['channelTitle'],
            'video_url': r''.join(("http://youtu.be/", video_id)),
            'views': response['items'][0]['statistics']['viewCount'],
            'likes': response['items'][0]['statistics']['likeCount'],
            'published_date': response['items'][0]['snippet']['publishedAt'] 
        }     

        return video_info

if __name__ == '__main__':

    YOUTUBE_API_KEY = ReadApiKeys.youtube_api_key()
    handler = AnalysisHandle(YOUTUBE_API_KEY)
    video_ID = "ZbwV_W9HjnY"

    video_info = handler.fetch_youtube_video_comments_with_sentiments(video_ID)
    with open("videoinfo.json", "+w") as file:
        json.dump(video_info, file)