import os
import googleapiclient.discovery
import requests
from transformers import pipeline
from tqdm import tqdm
from utils import ReadApiKeys, Cache

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

class SentimentAnalyzer:

    text_perception_analyzer = pipeline(
        model="lxyuan/distilbert-base-multilingual-cased-sentiments-student", 
        top_k=1
        )

    def get_sentiment_from_text(self, text: str) -> str:
        '''Uses lxyuan/distilbert-base-multilingual-cased-sentiments-student to get the perception of a text. This can be ``positive``, ``neutral`` or ``negative``
        Returns the label of the text's principal sentiment.'''

        # pass the text to the model to get a response
        response = self.text_perception_analyzer(text)

        # return the label of the top 1 sentiment
        return response[0][0]['label']


class YoutubeConnection:
    '''ApiHandle contains necessary functions to connect with YouTube and Hugging Face API.
    which are used in analysis functions in this exercise.
    
    YOUTUBE_API_KEY: YouTube API key.
    '''

    def __init__(self, YOUTUBE_API_KEY: str) -> None:
        self.YOUTUBE_API_KEY = YOUTUBE_API_KEY

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
            print(f"Error in YouTube connection.")
            print(f"Reason: {error.reason}")
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


    
class DataCleaner:
    def extract_comment_text_and_date(self, youtube_response_json: list) -> list[dict[str, str]]:
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

            comments = [
                {
                    'text': comment['snippet']['topLevelComment']['snippet']['textDisplay'], 
                    'date': comment['snippet']['topLevelComment']['snippet']['updatedAt']
                } 
                for response in youtube_response_json for comment in response
                ]

            return comments
    
    def extract_video_relevant_info(self, video_info_response_json: dict) -> dict[str, str]:
        video_info = {
            'thumbnail_url': video_info_response_json['items'][0]['snippet']['thumbnails']['high']['url'],
            'video_title': video_info_response_json['items'][0]['snippet']['title'],
            'channel_name': video_info_response_json['items'][0]['snippet']['channelTitle'],
            'video_url': "youtu.be/"+video_info_response_json['items'][0]["id"],
            'views': video_info_response_json['items'][0]['statistics']['viewCount'],
            'likes': video_info_response_json['items'][0]['statistics']['likeCount'],
            'published_date': video_info_response_json['items'][0]['snippet']['publishedAt'] 
        }     

        return video_info
    

    
class CommentLengthChecker:

    def check_if_comments_list_length_is_too_long(self, comments_data: list[dict[str, str]]) -> bool:
        return True if len(comments_data) >= 10000 else False
    
    def check_if_comments_length_is_too_long(self, comment) -> bool:
        return True if len(comment) >= 512 else False
    
    def clean_comments_list(self, comments_data: list[dict[str, str]]) -> list[dict[str, str]]:
        if self.check_if_comments_list_length_is_too_long(comments_data):
            return comments_data[:10000]
        
        else:
            return comments_data

    def clean_comments_too_long(self) -> list[dict[str, str]]:
        pass

    
class CommentAnalyzer:
    '''This class works with'''

    processed = False

    def __init__(self, comments_data: list[dict[str, str]]) -> None:
        self.comments_data = comments_data        

    def add_emotions_to_comments_data(self) -> None:

        for comment in tqdm(range(len(0, self.comment_data + 1))):
            comment['sentiment'] = self.SentimentAnalyzer.get_sentiment_from_text(comment['text'])
    
        self.processed = True
    
    def get_comments_with_sentiment(self) -> list[dict[str, str]]:
        if self.processed:
            return self.comments_data
        else:
            self.add_emotions_to_comments_data()
            self.get_comments_with_sentiment()
        
class CommentsOfVideoSentimentAnalyzer:

    sentiment_analyzer = SentimentAnalyzer()
    data_cleaner = DataCleaner()
    length_checker = CommentLengthChecker()
    comments_data = None
    comments_analyzer = CommentAnalyzer(comments_data)
    processed = False

    def __init__(self, youtube_connection: YoutubeConnection, video_id: str) -> None:
        self.youtube_connection = youtube_connection
        self.video_id = video_id

    def fetch_youtube_video_comments_with_sentiments(self):
        self.comments_data = self.youtube_connection.fetch_all_youtube_video_comments(self.video_id)
        self.comments_data = self.data_cleaner.extract_comment_text_and_date(self.comments_data)
        self.comments_analyzer.comments_data = self.comments_data
        # Add length checks.
        self.comments_analyzer.add_emotions_to_comments_data(self.comments_data)
        self.comments_data = self.comments_analyzer.get_comments_with_sentiment()

        self.processed = True

    def get_comments_data(self):
        if self.processed:
            return self.comments_data
        else:
            self.fetch_youtube_video_comments_with_sentiments()
            self.get_comments_data()

if __name__ == '__main__':

    YOUTUBE_API_KEY = ReadApiKeys.youtube_api_key()
    youtube_connection = YoutubeConnection(YOUTUBE_API_KEY)
    video_ID = "ZbwV_W9HjnY"
    handler = CommentsOfVideoSentimentAnalyzer(youtube_connection, video_ID)

    comments_data = handler.get_comments_data()
    cache = Cache()
    cache.create_cache_file(comments_data, video_ID)