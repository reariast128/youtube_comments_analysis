import os
import googleapiclient.discovery
import requests
from transformers import pipeline, Pipeline
from tqdm import tqdm
from utils import ReadApiKeys, Cache # just for debug things
from abc import ABC

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

class PipelineAnalyzer(ABC):
    '''Class for analyzing data using a pipeline model.'''

    model: Pipeline

    def apply_model_to_data(self, data):
        pass

class SentimentAnalyzer(PipelineAnalyzer):
    '''Class for analyzing the sentiment of text using a pipeline model.'''

    model = pipeline(
        model="lxyuan/distilbert-base-multilingual-cased-sentiments-student", 
        top_k=1
        )

    def apply_model_to_data(self, text: str) -> str:
        '''Uses lxyuan/distilbert-base-multilingual-cased-sentiments-student 
        to get the perception of a text. 
        This can be ``positive``, ``neutral`` or ``negative``
        Returns the label of the text's principal sentiment.'''

        # pass the text to the model to get a response
        response = self.model(text)

        # return the label of the top 1 sentiment
        return response[0][0]['label']
    


class Response(ABC):
    '''Abstract base class for handling responses.'''
    
    def __init__(self, data) -> None:
        self.data = data



class YoutubeResponse(Response):
    '''Class for handling responses from YouTube.'''
    
    def __init__(self, data) -> None:
        super().__init__(data)



class YoutubeVideoCommentsResponse(YoutubeResponse):
    '''Class for handling responses containing YouTube video comments.'''
    
    def __init__(self, data: list[dict[str, str]]) -> None:
        super().__init__(data)



class YoutubeVideoInfoResponse(YoutubeResponse):
    '''Class for handling responses containing information about YouTube videos.'''

    def __init__(self, data) -> None:
        super().__init__(data)



class Connection(ABC):
    '''Abstract base class for handling connections.'''

    def __build_connection(self):
        pass
    
    def fetch_data(self):
        pass    
    


class YoutubeConnection(Connection): 
    '''Class for establishing a connection with YouTube.'''

    def __init__(self, YOUTUBE_API_KEY: str, video_id: str) -> None:
        self.YOUTUBE_API_KEY = YOUTUBE_API_KEY
        self.video_id = video_id

    def __build_connection(self):
        pass
    
    def fetch_data(self):
        pass 
        


class YoutubeCommentsConnection(YoutubeConnection):
    '''Class for establishing a connection with YouTube to fetch video comments.
    Requires a Youtube API key to work.'''

    def __init__(self, YOUTUBE_API_KEY: str, video_id: str) -> None:
        super().__init__(YOUTUBE_API_KEY, video_id)

    def __build_connection(self, page_token: str = ''):
        # build the youtube connection
        youtube_connection = googleapiclient.discovery.build(
            'youtube', 'v3', developerKey=self.YOUTUBE_API_KEY)
        
        request = youtube_connection.commentThreads().list(
                part="snippet,replies",
                videoId=self.video_id,
                maxResults=100,
                pageToken=page_token
            )
        
        return request

    def fetch_data(self, page_token: str = '') -> dict:
        '''Fetches the comments JSON of a YouTube video using googleapiclient.
        `page_token` is an optional argument, that indicates to request 
        to fetch only a comments page from the whole comments available in the video.
        '''

        request = self.__build_connection(page_token=page_token)
            
        # trying request and handling with possible errors
        try:
            response = request.execute()
            
        except googleapiclient.discovery.HttpError as error:
            print(f"Error in YouTube connection.")
            print(f"Reason: {error.reason}")
            raise googleapiclient.discovery.HttpError

        else:
            print(f"Request id {response['etag']} was executed successfully.")
            return response

    def fetch_all_youtube_video_comments(self) -> YoutubeVideoCommentsResponse:
        '''Retrieves a JSON with all the comments page from a video using fetch_youtube_video_comments function.'''
        responses = []
        try:
            print(f"Trying to get all comments from {self.video_id} video.")
            response = self.fetch_data()
            responses.append(response)

            while 'nextPageToken' in response.keys():
                next_page_token = response['nextPageToken']
                response = self.fetch_data(page_token=next_page_token)
                responses.append(response)

            return YoutubeVideoCommentsResponse(responses)
        
        except googleapiclient.discovery.HttpError as error:
            error_reason = error.error_details
            print(f"Error in YouTube connection.")
            print(f"Reason: {error_reason}")
            raise

        except Exception as error:
            print(f"An error occurred: {error}")
            raise



class YoutubeVideoInfoConnection(YoutubeConnection):
    '''Class for establishing a connection with YouTube to fetch video information.
    Requires a Youtube API key to work.'''
     
    def __init__(self, YOUTUBE_API_KEY: str, video_id: str) -> None:
        super().__init__(YOUTUBE_API_KEY, video_id)

    def __build_connection(self):
        return f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet%2CcontentDetails%2Cstatistics&id={self.video_ID}&key={self.YOUTUBE_API_KEY}"

    def fetch_data(self) -> dict:
        '''Get the JSON with the video info using a HTTPS request.'''
        request_url = self.__build_connection()
        try:
            response = requests.get(request_url)
            if response.status_code == 200:
                return YoutubeVideoInfoResponse(response.json())
            
            else:
                raise requests.HTTPError
            
        except requests.HTTPError as error:
            print(f"Failed to get YouTube video information: {error.strerror}")
            raise requests.HTTPError
        
        except Exception as error:
            print(f"An error occurred: {error}")



class Cleaner(ABC):
    '''Baseclass for data cleaning tasks.'''

    def check_if_clean_is_needed(self, data):
        pass

    def clean_data(self, data):
        pass



class YoutubeVideoCommentsListLengthCleaner(Cleaner):
    '''Class for cleaning the response containing YouTube video comments. 
    Filters out comments that exceed a certain length.'''

    def check_if_clean_is_needed(self, comments_data: list[dict[str, str]]) -> bool:
        return True if len(comments_data) >= 10000 else False
    
    def clean_data(self, comments_data: list[dict[str, str]]) -> list[dict[str, str]]:
        return comments_data[:10000] if self.check_if_clean_is_needed(comments_data) else comments_data
        

    
class YoutubeVideoCommentLengthCleaner(Cleaner):
    '''Class for cleaning individual YouTube video comments. 
    Filters out comments that exceed a certain length.'''
    
    def check_if_clean_is_needed(self, comment: str) -> bool:
        return True if len(comment) >= 512 else False
    
    def clean_data(self):
        raise NotImplementedError
    

    
class YoutubeVideoCommentsDataCleaner(Cleaner):
    '''Class for cleaning the response containing YouTube video comments. 
    Filters out comments that exceed a certain length and/or a certain number of comments.'''

    def check_if_clean_is_needed(self, data):
        raise NotImplementedError
    
    def clean_data(self, youtube_comments: YoutubeVideoCommentsResponse) -> YoutubeVideoCommentsResponse:
        comments_length_cleaner = YoutubeVideoCommentLengthCleaner()
        list_length_cleaner = YoutubeVideoCommentsListLengthCleaner()

        '''This method clean the Youtube Response JSON data, and leaves only the "text" and the "date" from the original response, to be used to analyze sentiments.'''
        cleaned_comments_list: list[dict[str, str]] = [
            {
                'text': comment['snippet']['topLevelComment']['snippet']['textDisplay'], 
                'date': comment['snippet']['topLevelComment']['snippet']['updatedAt']
            } 
            for response in youtube_comments.data for comment in response['items']
            if not comments_length_cleaner.check_if_clean_is_needed(comment['snippet']['topLevelComment']['snippet']['textDisplay'])]
        
        cleaned_comments_list = list_length_cleaner.clean_data(cleaned_comments_list)
        
        return YoutubeVideoCommentsResponse(cleaned_comments_list)



class YoutubeVideoInfoCleaner(Cleaner):
    '''Class for cleaning the response containing YouTube video comments. 
    Filters out comments that exceed a certain length and/or a certain number of comments.'''

    def check_if_clean_is_needed(self):
        raise NotImplementedError
    
    def clean_data(self, video_info):
        video_info = {
            'thumbnail_url': video_info['items'][0]['snippet']['thumbnails']['high']['url'],
            'video_title': video_info['items'][0]['snippet']['title'],
            'channel_name': video_info['items'][0]['snippet']['channelTitle'],
            'video_url': "youtu.be/"+video_info['items'][0]["id"],
            'views': video_info['items'][0]['statistics']['viewCount'],
            'likes': video_info['items'][0]['statistics']['likeCount'],
            'published_date': video_info['items'][0]['snippet']['publishedAt'] 
        }     

        return video_info



class CommentAnalyzer:
    '''Class for analyzing comments data of a YouTube video.'''

    processed = False

    def __init__(self, comments_data: YoutubeVideoCommentsResponse) -> None:
        self.comments_data = comments_data.data     
        self.sentiment_analyzer = SentimentAnalyzer()

    def add_emotions_to_comments_data(self) -> None:
        '''Adds sentiment analysis to each comment in the data.'''
        
        for comment in tqdm(range(0, len(self.comments_data))):
            self.comments_data[comment]['sentiment'] = self.sentiment_analyzer.apply_model_to_data(self.comments_data[comment]['text'])
    
        self.processed = True
    
    def get_comments_with_sentiment(self) -> list[dict[str, str]]:
        '''Returns comments data with sentiment analysis. Processes data if not already processed.'''

        if self.processed:
            return self.comments_data
        else:
            self.add_emotions_to_comments_data()
            self.get_comments_with_sentiment()
        
class CommentsOfVideoSentimentAnalyzer:
    '''Class for analyzing sentiments of comments from a YouTube video.'''

    sentiment_analyzer = SentimentAnalyzer()
    comments_cleaner = YoutubeVideoCommentsDataCleaner()
    processed = False

    def __init__(self, youtube_connection: YoutubeCommentsConnection) -> None:
        self.youtube_connection = youtube_connection

    def fetch_youtube_video_comments_with_sentiments(self):
        '''Fetches YouTube video comments with sentiment analysis.'''
        # Fetching all comments from a video.
        self.comments_data = self.youtube_connection.fetch_all_youtube_video_comments()

        # Extracting only comment text and date (and cleaning comments if list is longer than 10000 comments or if comments are longer than 512 characters.)
        self.comments_data = self.comments_cleaner.clean_data(self.comments_data)
        
        # Adding sentiments to each comment registry.
        comments_analyzer = CommentAnalyzer(self.comments_data)
        self.comments_data = comments_analyzer.get_comments_with_sentiment()

        self.processed = True

    def get_comments_data(self):
        '''Returns comments data with sentiment analysis. Fetches data if not already processed.'''
        if self.processed:
            return self.comments_data
        else:
            self.fetch_youtube_video_comments_with_sentiments()
            self.get_comments_data()

if __name__ == '__main__':

    YOUTUBE_API_KEY = ReadApiKeys().youtube_api_key()
    video_ID = "ZbwV_W9HjnY"
    youtube_connection = YoutubeCommentsConnection(YOUTUBE_API_KEY, video_ID)
    sentiments_analyzer = CommentsOfVideoSentimentAnalyzer(youtube_connection)

    comments_analyzed = sentiments_analyzer.get_comments_data()
    cache = Cache()
    cache.create_cache_file(comments_analyzed, video_ID)