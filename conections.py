import os
import googleapiclient.discovery
import requests
from transformers import pipeline
from tqdm import tqdm
from utils import ReadApiKeys, Cache # just for debug things
from abc import ABC, abstractmethod

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

class SentimentAnalyzer:

    text_perception_analyzer = pipeline(
        model="lxyuan/distilbert-base-multilingual-cased-sentiments-student", 
        top_k=1
        )

    def get_sentiment_from_text(self, text: str) -> str:
        '''Uses lxyuan/distilbert-base-multilingual-cased-sentiments-student 
        to get the perception of a text. 
        This can be ``positive``, ``neutral`` or ``negative``
        Returns the label of the text's principal sentiment.'''

        # pass the text to the model to get a response
        response = self.text_perception_analyzer(text)

        # return the label of the top 1 sentiment
        return response[0][0]['label']

# Maybe can create an dataclass that represents Video Data?
class YoutubeConnection(ABC):
    '''YoutubeConnection contains the necessary functions to connect with YouTube API.
    
    YOUTUBE_API_KEY: YouTube API key.
    '''

    def __init__(self, YOUTUBE_API_KEY: str, video_id: str) -> None:
        self.YOUTUBE_API_KEY = YOUTUBE_API_KEY
        self.video_id = video_id

    def fetch_data(self):
        pass

    def build_connection(self):
        pass

   

class YoutubeCommentsConnection(YoutubeConnection):

    def __init__(self, YOUTUBE_API_KEY: str, video_id: str) -> None:
        super().__init__(YOUTUBE_API_KEY, video_id)

    def build_connection(self, page_token: str = ''):
        # build the youtube connection
        youtube_connection = googleapiclient.discovery.build(
            'youtube', 'v3', developerKey = self.YOUTUBE_API_KEY)
        
        request = youtube_connection.commentThreads().list(
                part="snippet,replies",
                videoId=self.video_id,
                maxResults=100,
                pageToken=page_token
            )
        
        return request

    def fetch_data(self, page_token: str = '') -> dict:
        '''Get the comments JSON of a YouTube video using googleapiclient.
        `page_token` is an optional argument, that indicates to request 
        to fetch only a comments page from the whole comments avaiable in the video.
        '''

        request = self.build_youtube_connection(page_token=page_token)
            
        # trying request and handling with possible errors
        try:
            response = request.execute() # type: ignore
            if 'error' in response.keys():
                raise requests.HTTPError

            else:
                print(f"Request id {response['etag']} was executed sucessfully.")
                return response
            
        except googleapiclient.discovery.HttpError as error:
            print(f"Error in YouTube connection.")
            print(f"Reason: {error.reason}")
            raise

    def fetch_all_youtube_video_comments(self, video_ID: str) -> list:
        '''Retrieves a JSON with all the comments page from a video using fetch_youtube_video_comments function.'''
        responses = []
        try:
            print(f"Trying to get all comments from {video_ID} video.")
            response = self.fetch_data(video_ID)
            responses.append(response)

            while 'nextPageToken' in response.keys():
                next_page_token = response['nextPageToken']
                response = self.fetch_data(video_ID, page_token=next_page_token)
                responses.append(response)

            return responses
        
        except googleapiclient.discovery.HttpError as error:
            error_reason = error.error_details
            print(f"Error in YouTube connection.")
            print(f"Reason: {error_reason}")
            raise



class YoutubeVideoInfoConnection(YoutubeConnection):
     
    def __init__(self, YOUTUBE_API_KEY: str, video_id: str) -> None:
        super().__init__(YOUTUBE_API_KEY, video_id)

    def build_connection(self):
        return f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet%2CcontentDetails%2Cstatistics&id={self.video_ID}&key={self.YOUTUBE_API_KEY}"

    def fetch_data(self) -> dict:
        '''Get the JSON with the video info using a HTTPS request.'''
        request_url = self.build_connection()
        try:
            response = requests.get(request_url)
            if response.status_code == 200:
                return response.json()
            else:
                raise requests.HTTPError
        except requests.HTTPError:
            raise 

class Cleaner(ABC):

    def check_is_clean_is_needed(self, data):
        pass

    def clean_data(self):
        pass

# Maybe can turn this into an abstract class?
class CommentsListLengthCleaner(Cleaner):

    def check_is_clean_is_needed(self, comments_data: list[dict[str, str]]) -> bool:
        return True if len(comments_data) >= 10000 else False
    
    def clean_data(self, comments_data: list[dict[str, str]]) -> list[dict[str, str]]:
        return comments_data[:10000] if self.check_is_clean_is_needed() else comments_data
        

    
class CommentLengthCleaner(Cleaner):
    
    def check_is_clean_is_needed(self, comments: str) -> bool:
        return True if len(comments) >= 512 else False
    
    def clean_data(self):
        raise NotImplementedError
    

    
class VideoInfoCleaner(Cleaner):

    def __init__(self, data) -> None:
        super().__init__(data)

    def check_is_clean_is_needed(self):
        raise NotImplementedError
    
    def clean_data(self):
        video_info = {
            'thumbnail_url': self.data['items'][0]['snippet']['thumbnails']['high']['url'],
            'video_title': self.data['items'][0]['snippet']['title'],
            'channel_name': self.data['items'][0]['snippet']['channelTitle'],
            'video_url': "youtu.be/"+self.data['items'][0]["id"],
            'views': self.data['items'][0]['statistics']['viewCount'],
            'likes': self.data['items'][0]['statistics']['likeCount'],
            'published_date': self.data['items'][0]['snippet']['publishedAt'] 
        }     

        return video_info


# Maybe can turn this into an abstract class?
class CommentsCleaner:

    def __init__(self, youtube_response_json) -> None:
        self.youtube_response_json = youtube_response_json
        self.comments_list_length_cleaner = CommentsListLengthCleaner()
        self.comments_length_cleaner = CommentLengthCleaner()

    def extract_comment_text_and_date(self, youtube_response_json: list) -> list[dict[str, str]]:
        '''Returns a list with relevant data of the 
        YouTube's response list. Also, removes all 
        the comments which text is longer than
        512 characters, and removes all elements 
        which index is longer than 10000.
        Returns a list like this:
            [
                {
                    'text': 'This is a comment',
                    'date': '2023-11-24T03:57:00Z'
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
            if not self.comments_list_length_cleaner.check_is_clean_is_needed(comment['snippet']['topLevelComment']['snippet']['textDisplay'])
            ]
        
        comments = self.comments_list_length_cleaner.clean_data(comments) if self.comments_list_length_cleaner.check_is_clean_is_needed() else comments

        return comments
    
class VideoInfoCleaner:

    def extract_video_relevant_info(self, video_info_response_json: dict) -> dict[str, str]:
        '''Returns a '''
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


    
class CommentAnalyzer:

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
        # Fetching all comments from a video.
        self.comments_data = self.youtube_connection.fetch_all_youtube_video_comments(self.video_id)

        # Extracting only comment text and date (and cleaning comments if list is longer than 10000 comments or if comments are longer than 512 characters.)
        self.comments_data = self.data_cleaner.extract_comment_text_and_date(self.comments_data)
        
        # Adding sentiments to each comment registry.
        self.comments_analyzer.comments_data = self.comments_data
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