from tkinter import ttk
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
import urllib.request
from PIL import ImageTk, Image
import io
import data_transformation
import conections
import threading
from utils import Cache
import datetime
from queue import Queue, Empty

class PltAndTkPlots():
    '''This module works with comments_json structure.
    root: Parent frame to draw the plots.'''

    def __init__(self, root, comments_data) -> None:
        self.root = root
        self.comments_data = comments_data

    def _video_comments_over_time(self, frame) -> None:
        # obtain data to plot 
        data_handler = data_transformation.DataTransformations(self.comments_data)
        data = data_handler.comments_over_time()

        # create a figure with an specific size and resolution
        fig = Figure(figsize=(12, 7), dpi=100)

        # create a subplot to the figure and draw the plot
        subplot = fig.add_subplot(111)
        subplot.plot(data['date'], data['count'])
        subplot.set_title("Video comments over time")
        subplot.xaxis.set_tick_params(rotation=45)

        # create a tkinter canvas and draw the plot into it
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()

        # embed the canvas into the specified position
        canvas.get_tk_widget().grid(row=10, column=00)

        # create the toolkit
        toolbar_subframe = ttk.Frame(master=self.root)
        toolbar_subframe.grid(row=20, column=0)

        # draw toolkit in the bottom of the frame
        NavigationToolbar2Tk(canvas, toolbar_subframe)
    
    def _video_sentiments_over_time(self, frame):
        # obtain data
        data_handler = data_transformation.DataTransformations(self.comments_data)
        sentiments = data_handler.sentiment_across_time()

        # create the figure that contains the plot
        fig = Figure(figsize=(12, 7), dpi=100)
        subplot = fig.add_subplot(111)

        for name, group in sentiments:
            subplot.plot(group['date'], group['count'], label=name)

        # set tag to each axis
        subplot.set_xlabel('Date')
        subplot.set_ylabel('Count')
        subplot.set_title('Sentiments count over time')

        # add a legend
        subplot.legend()

        # rotate the labels of x-axis
        subplot.xaxis.set_tick_params(rotation=45)

        # create a tkinter canvas an draw the plot into it
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()

        # embed the canvas into the specified position
        canvas.get_tk_widget().grid(row=10, column=0)

        # create the toolkit
        toolbar_subframe = ttk.Frame(master=self.root)
        toolbar_subframe.grid(row=20, column=0)

        # draw toolkit in the bottom of the frame
        NavigationToolbar2Tk(canvas, toolbar_subframe)
    
    def _video_sentiment_count(self, frame):
        data_handler = data_transformation.DataTransformations(self.comments_data)
        sentiments_count = data_handler.count_sentiments()

        fig = Figure(figsize=(12, 7), dpi=100)
        subplot = fig.add_subplot(111)
        subplot.bar(sentiments_count['sentiment'], sentiments_count['count'])

        subplot.set_xlabel("Sentiment category")
        subplot.set_ylabel("Count")
        subplot.set_title("Sentiment count")

        # create a tkinter canvas an draw the plot into it
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()

        # embed the canvas into the specified position
        canvas.get_tk_widget().grid(row=10, column=0)

        # create the toolkit
        toolbar_subframe = ttk.Frame(master=self.root)
        toolbar_subframe.grid(row=20, column=0)

        # draw toolkit in the bottom of the frame
        NavigationToolbar2Tk(canvas, toolbar_subframe)

class PlotDrawer(PltAndTkPlots):

    def __init__(self, root, comments_data) -> None:
        super().__init__(root, comments_data)

    def draw_plots(self, notebook_parent_frame: ttk.Notebook):
        _video_comments_over_time_frame = ttk.Frame(notebook_parent_frame)
        self._video_comments_over_time(_video_comments_over_time_frame)
        
        _video_sentiment_count_frame = ttk.Frame(notebook_parent_frame)
        self._video_sentiment_count(_video_sentiment_count_frame)

        _video_sentiments_over_time_frame = ttk.Frame(notebook_parent_frame)
        self._video_sentiments_over_time(_video_sentiments_over_time_frame)

        notebook_parent_frame.add(_video_comments_over_time_frame, text="Comments over time")
        notebook_parent_frame.add(_video_sentiment_count_frame, text="Sentiments count")
        notebook_parent_frame.add(_video_sentiments_over_time_frame, text="Sentiments over time")


class gui_builder():

    def __init__(self, API_KEY) -> None:
        self.root = ttk.Tk()
        self.video_id_str = ttk.StringVar()
        self.queue = Queue()
        self.video_thumbnail = None
        self.API_KEY = API_KEY

    def check_queue(self):
        try:
            # Intentar obtener datos de la cola
            comments, video_info = self.queue.get_nowait()
            self.draw_video_info_and_stats(video_info)
            self.draw_mainframe(comments)
        except Empty:
            # Si la cola está vacía, volver a comprobar después de un corto retraso
            self.root.after(100, self.check_queue)

    def get_image(self, url):
        response = urllib.request.urlopen(url)
        image_data = response.read()
        image_bytes = io.BytesIO(image_data)
        img = Image.open(image_bytes)
        
        return ImageTk.PhotoImage(img)

    def draw_video_info_and_stats(self, video_info):
        video_info_frame = ttk.Frame(self.root)
        video_info_frame.grid(row=0, column=10)

        self.video_thumbnail = self.get_image(video_info['thumbnail_url'])
        video_thumbnail_label = ttk.Label(video_info_frame, image=self.video_thumbnail)
        video_thumbnail_label.grid(row=1, column=10, columnspan=30)

        video_name_label = ttk.Label(video_info_frame, text="Name:")
        video_name_label.grid(row=10, column=10)

        video_name = ttk.Label(video_info_frame, text=video_info['video_title'], wraplength=200)
        video_name.grid(row=10, column=20,)

        video_creator_label = ttk.Label(video_info_frame, text="Creator:")
        video_creator_label.grid(row=20, column=10)

        video_creator_name = ttk.Label(video_info_frame, text=video_info['channel_name'])
        video_creator_name.grid(row=20, column=20)

        views_label = ttk.Label(video_info_frame, text=f"Views: {video_info['views']}")
        views_label.grid(row=30, column=20)

        likes_label = ttk.Label(video_info_frame, text=f"Likes: {video_info['likes']}")
        likes_label.grid(row=30, column=30)

        date = datetime.datetime.strptime(video_info['published_date'], "%Y-%m-%dT%H:%M:%SZ")
        date = date.strftime("%B %d, %Y")

        published_label = ttk.Label(video_info_frame, text=f"Uploaded at {date}")
        published_label.grid(row=30, column=10)

    def draw_mainframe(self, comments_data):
        plot_notebook = ttk.Notebook(self.root)

        # draw plots
        PlotDrawer(self.root, comments_data).draw_plots(plot_notebook)
        plot_notebook.grid(row=0, column=0, padx=10)

    def load_plots_info(self):
        conections_handler = conections.AnalysisHandle(self.API_KEY)

        comments = None
        video_info = conections_handler.fetch_video_info_and_stats(self.video_id_str.get())
        
        if Cache.check_if_cache_file_exist(self.video_id_str.get()):
            comments = Cache.get_cache_file(self.video_id_str.get())
        else:
            comments = conections_handler.fetch_youtube_video_comments_with_sentiments(self.video_id_str.get())
            Cache.create_cache_file(comments, self.video_id_str.get())

        self.queue.put((comments, video_info))

    def input_box(self):
        window = ttk.Toplevel(self.root)
        window.geometry("150x150")

        window.title("Type the video ID.")

        title_label = ttk.Label(window, text="Type the video ID.")
        title_label.grid(row=0, column=0, padx=10, pady=10)

        self.video_id_str = ttk.StringVar(window)
        video_id_entry = ttk.Entry(window, textvariable=self.video_id_str)
        video_id_entry.grid(row=1, column=0, padx=10, pady=10)

        submit_button = ttk.Button(window, text="Submit", command=self.on_submit_click)
        submit_button.grid(row=2, column=0, padx=10, pady=10)

    def on_submit_click(self):
        thread = threading.Thread(target=self.load_plots_info)
        thread.start()
        # Comienza a verificar la cola para ver si hay datos disponibles
        self.root.after(100, self.check_queue)

    def start(self):
        self.input_box()
        self.root.mainloop()