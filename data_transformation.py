import pandas as pd

class DataTransformations:
    def __init__(self, data) -> None:
        if type(data) == 'DataFrame':
            self.df = data
        else:
            self.df = pd.DataFrame(data=data)

    def comments_over_time(self):
        # Transform date column to date data type
        self.df['date'] = pd.to_datetime(self.df['date']).dt.date

        # Group by date and count comments in each date
        message_counts = self.df.groupby('date').size().reset_index(name='count')

        # Sort by date
        message_counts = message_counts.sort_values('date')

        return message_counts

    def sentiment_across_time(self):
        # Transform date column to date data type
        self.df['date'] = pd.to_datetime(self.df['date']).dt.date

        # Group comments by date and sentiment
        sentiments_across_time_table = self.df.groupby(['date', 'sentiment']).size()

        # Add count column, that contains the sum of each sentiment by date
        sentiments_across_time_table = sentiments_across_time_table.reset_index(name='count')
        sentiments_across_time_table_grouped = sentiments_across_time_table.groupby('sentiment')

        return sentiments_across_time_table_grouped
    
    def count_sentiments(self):
        # Group by sentiment and count by sentiment
        sentiments_count = self.df.groupby('sentiment').size().reset_index(name='count')
        return sentiments_count