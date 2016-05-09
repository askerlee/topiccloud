import warnings
from random import Random
from os import path
from wordcloud.wordcloud import WordCloud, IntegralOccupancyMap
from operator import itemgetter
import numpy as np
import pdb
import colorsys
from nltk.stem.wordnet import WordNetLemmatizer
from morpha import lemmatize
import re

from PIL import Image
from PIL import ImageColor
from PIL import ImageDraw
from PIL import ImageFont

def str2dict(s):
    wordlist = re.split( "\s+", s )
    worddict = {}    
    for w in wordlist:
        worddict[w] = 1
    return worddict

#lmtzr = WordNetLemmatizer()
random_state = Random()
img_padding = 15

specialNounsStr = "embeddings"
specialVerbsStr = ""
specialNounDict = str2dict(specialNounsStr)
specialVerbDict = str2dict(specialVerbsStr)
originalStr = "embedding turing sinai saudi data"
originalDict = str2dict(originalStr)

def clockwise(start_angle, stop_angle):
    start_angle = start_angle % 360
    stop_angle = stop_angle % 360
    # clockwise (90 degree at bottom, as the custom of pillow), start is the first and stop is the second
    # so start_angle < stop_angle
    if stop_angle < start_angle:
        if start_angle - stop_angle < 180:
            start_angle, stop_angle = stop_angle, start_angle
        else:
            stop_angle += 360
            
    return start_angle, stop_angle
    
def genSectorMask( width, height, start_angle, stop_angle ):

    start_angle, stop_angle = clockwise(start_angle, stop_angle)
    sector_mask = np.ones( (height, width) )
    origin_x = width / 2
    origin_y = height / 2
    sin1 = np.sin( start_angle * np.pi / 180 )
    cos1 = np.cos( start_angle * np.pi / 180 )
    sin2 = np.sin( stop_angle * np.pi / 180 )
    cos2 = np.cos( stop_angle * np.pi / 180 )
    reservedCenterRadius = 5
    maxRadius = min(width, height) * 0.5 - img_padding
    for y in xrange(height):
        for x in xrange(width):
            x2 = x - origin_x
            y2 = (height - y) - origin_y
            radius = np.sqrt(x2*x2 + y2*y2)
            if radius >= reservedCenterRadius and radius <= maxRadius and sin1 * x2 <= -cos1 * y2 and sin2 * x2 >= -cos2 * y2:
                sector_mask[y,x] = 0
    
    return sector_mask

def d3_category20_rand(topicID):
    d3_category20 = [   # "#aec7e8", "#ffbb78", "#98df8a", 
                        # "#d62728", too striking red, "#ff7f0e", orange is alerting; 
                        # "#bcbd22", ugly; "#e377c2", striking
                        "#2ca02c", "#9467bd", "#1f77b4", "#ff9896", 
                        "#17becf", "#7f7f7f", "#8c564b", "#c49c94" ]
                        #   ""#c5b0d5", "#c49c94", 
                        #   "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5"
    colorID = topicID % len(d3_category20)
    basecolor = d3_category20[colorID]
    r, g, b = ImageColor.getrgb(basecolor)
    fluc = 60
    r += random_state.randint( 0, fluc ) - fluc/2
    g += random_state.randint( 0, fluc ) - fluc/2
    b += random_state.randint( 0, fluc ) - fluc/2
    r = min( max(r, 0), 255 )
    g = min( max(g, 0), 255 )
    b = min( max(b, 0), 255 )
    return "rgb(%d, %d, %d)" %(r, g, b)

def lemmatize2(word):
    if word in originalDict:
        return word
        
    candidatePOSs = ('n', 'v')
    
    if word in specialNounDict:
        candidatePOSs = [ 'n' ]
    if word in specialVerbDict:
        candidatePOSs = [ 'v' ]
        
    for pos in candidatePOSs:
        #w2 = lmtzr.lemmatize(word, pos)
        w2 = lemmatize(word, pos)
        if w2 != word:
            return w2
    return word
        
class TopicCloud(WordCloud):
    def __init__(self, min_sector_padding=0, max_topic_num=10, max_sector_angle=150, max_topic_prop_ratio=6, 
                    min_sector_angle=20, max_topic_words=10, min_word_topic_prop=0.5, **kwargs):
        super(TopicCloud, self).__init__(**kwargs)
        self.min_sector_padding = min_sector_padding
        self.max_topic_num = max_topic_num
        self.max_sector_angle = max_sector_angle
        self.min_sector_angle = min_sector_angle
        self.max_topic_prop_ratio = max_topic_prop_ratio
        self.max_topic_words = max_topic_words
        self.min_word_topic_prop = min_word_topic_prop
        self.margin = 4
        self.font_path = "C:/Windows/fonts/impact.ttf"
        self.background_color = "white"
        self.prefer_horizontal = 1
        
    def generate_from_topics(self, topics):
        """Create a topic_cloud from topics.

        Parameters
        ----------
        topics : array of tuples
                 Each topic: (proportion in the document, [ (word1, freq1), (word2, freq2), ... ] )

        Returns
        -------
        self

        """

        # lemmatizing
        for topic in topics:  
            words_freq = topic[1]
            words_freq2 = []
            word2idx = {}
            idx = 0
            for word, freq in words_freq:
                word2 = lemmatize2(word)
                if word2 in word2idx:
                    wid = word2idx[word2]
                    words_freq2[wid][1] += freq
                else:
                    words_freq2.append( [word2, freq] )
                    word2idx[word2] = idx
                    idx += 1
                                
            words_freq2 = sorted(words_freq2, key=itemgetter(1), reverse=True)
            for i in xrange( len(words_freq2)-1, -1, -1 ):
                if words_freq2[i][1] >= self.min_word_topic_prop:
                    break
            words_freq2 = words_freq2[:i+1]
                            
            topic[1] = words_freq2[:self.max_topic_words]
            # topic_mass = sum( [ len(w) for (w,f) in topic[1] ] )
            # topic_masses.append(topic_mass)
            #topic[0] *= topic[1][0][1] * sum( [ word_freq[1] for word_freq in topic[1] ] )
            
        # make sure topics are sorted and normalized
        topics = sorted( topics, key=itemgetter(0), reverse=True )
        if len(topics) > self.max_topic_num:
            topics = topics[:self.max_topic_num]
        min_topic_prop = topics[0][0] / self.max_topic_prop_ratio
        for i in xrange( len(topics)-1, 0, -1 ):
            if topics[i][0] >= min_topic_prop:
                break
        topics = topics[:i+1]
        T = len(topics)

        #topic_masses = []
        topic_masses = np.ones(T)
                    
        # sqrt for smoothing    
        total_props = sum( [ np.power(topics[i][0] * topic_masses[i],0.8) for i in xrange(len(topics)) ] )
        for i in xrange(len(topics)):
            topics[i][0] = np.power(topics[i][0] * topic_masses[i],0.8) / total_props
        
        avail_angles = 360 - T * self.min_sector_padding
        max_angle = avail_angles * topics[0][0]
        angle_scale = 1
        if max_angle > self.max_sector_angle:
            angle_scale = self.max_sector_angle / max_angle
        topic_angles = []
        for topic in topics:
            topic_angles.append( avail_angles * topic[0] * angle_scale )
        sector_padding = ( 360 - sum(topic_angles) ) / T
        topic_angles = np.array(topic_angles)

        height, width = self.height, self.width
        # create image
        img_grey = Image.new("L", (width, height))
        draw = ImageDraw.Draw(img_grey)
        img_array = np.asarray(img_grey)
        total_freqs, font_sizes, positions, orientations, colors = [], [], [], [], []

        if self.random_state is not None:
            random_state = self.random_state
        else:
            random_state = Random()

        sector_masks = []
        sector_angles = []
        
        for i,topic in enumerate(topics):
            width = self.width
            height = self.height
            last_freq = 1.
            font_size = self.max_font_size * min( np.sqrt(topic[1][0][1] / topics[0][1][0][1]), 2 )
            
            if i == 0:
                # initial angle starts from the symmetric left side of the y-axis
                # to ensure first sector always at right above of the canvas
                start_angle = 270 - topic_angles[0]/2 
                stop_angle = 270 + topic_angles[0]/2
            else:
                start_angle = stop_angle + sector_padding
                stop_angle += sector_padding + topic_angles[i]

            # reverse sign to conform with pillow's measurement of angles
            sector_angles.append( clockwise(start_angle, stop_angle) )
            #print "%.1f - %.1f =>" %( start_angle % 360, stop_angle % 360),
            #print "%.1f - %.1f" %( clockwise(start_angle, stop_angle) )
            
            sector_mask = genSectorMask( width, height, start_angle, stop_angle )
            sector_masks.append(sector_mask)
            occupancy = IntegralOccupancyMap(height, width, sector_mask)

            frequencies = topic[1][:self.max_words]
            frequencies = sorted( frequencies, key=itemgetter(1), reverse=True )
            
            # largest entry will be 1
            max_frequency = float(frequencies[0][1])
    
            frequencies = [ (word, freq / max_frequency) for word, freq in frequencies ]
    
            if len(frequencies) == 0:
                print("We need at least 1 word to plot a word cloud, got 0.")
                continue
            
            total_freqs += frequencies
            drawn_words = []
            
            # start drawing grey image
            for word, freq in frequencies:
                # select the font size
                rs = self.relative_scaling
                if rs != 0:
                    font_size = int(round((rs * (freq / float(last_freq)) + (1 - rs)) * font_size))
                while True:
                    # try to find a position
                    font = ImageFont.truetype(self.font_path, font_size)
                    # transpose font optionally
                    if random_state.random() < self.prefer_horizontal:
                        orientation = None
                    else:
                        orientation = Image.ROTATE_90
                    transposed_font = ImageFont.TransposedFont(font,
                                                               orientation=orientation)
                    # get size of resulting text
                    box_size = draw.textsize(word, font=transposed_font)
                    # find possible places using integral image:
                    result = occupancy.sample_position(box_size[1] + 2 * self.margin,
                                                       box_size[0] + 2 * self.margin,
                                                       random_state)
                    if result is not None or font_size == 0:
                        break
                    # if we didn't find a place, make font smaller
                    font_size -= self.font_step
                        
                if font_size < self.min_font_size:
                    # we were unable to draw any more
                    font_size = self.min_font_size
                drawn_words.append(word)
                
                x, y = np.array(result) + self.margin // 2
                # actually draw the text
                draw.text((y, x), word, fill="white", font=transposed_font)
                positions.append((x, y))
                orientations.append(orientation)
                font_sizes.append(font_size)
                colors.append(d3_category20_rand(i))
                                              
                # recompute integral image
                img_array = ( np.asarray(img_grey) + sector_mask ) > 0
                # recompute bottom right
                # the order of the cumsum's is important for speed ?!
                occupancy.update(img_array, x, y)
                last_freq = freq
                
            print "Topic %d (%.1f):" %(i+1, topic_angles[i])
            print drawn_words
         
#        for i in xrange(len(sector_masks)):
#            for j in xrange(i):
#                if np.any( (1-sector_masks[i]) * (1-sector_masks[j]) ):
#                    pdb.set_trace()
                    
        self.layout_ = list(zip(total_freqs, font_sizes, positions, orientations, colors))
        self.sector_angles = sector_angles
        return self
    
    def to_image(self):
        self._check_generated()
        height, width = self.height, self.width

        img = Image.new(self.mode, (int(width * self.scale), int(height * self.scale)),
                        self.background_color)
                        
        draw = ImageDraw.Draw(img)
        bbox = (img_padding, img_padding, height-img_padding, height-img_padding)
        
        colors = [ "rgb(255,255,242)", "rgb(255,242,255)", "rgb(242,255,255)", "rgb(242,242,242)" ]
        i = 0
        if len(self.sector_angles) % len(colors) == 1:
            modulus = len(colors) - 1
        else:
            modulus = len(colors)
            
        for (start_angle, stop_angle) in self.sector_angles:
            draw.pieslice(bbox, start_angle, stop_angle, fill = colors[i%modulus])
            i += 1
            #print "%d-%d: %s" %(start_angle, stop_angle, colors[i%3])
            
        for (word, count), font_size, position, orientation, color in self.layout_:
            font = ImageFont.truetype(self.font_path, int(font_size * self.scale))
            transposed_font = ImageFont.TransposedFont(font,
                                                       orientation=orientation)
            pos = (int(position[1] * self.scale), int(position[0] * self.scale))
            draw.text(pos, word, fill=color, font=transposed_font)
        return img
            