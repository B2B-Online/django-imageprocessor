""" Easy image processing library using PIL """

"""
example usage:

    img = CachedImage('/tmp/my_image.png').thumbnail([120,80]).grayscale().render()
    img.save('/tmp/processed_image.png')
    print img.filename  # get output filename
    print img   # string (raw) representation

    change cache dir:

    img = CachedImage('/tmp/my_image.png').thumbnail([120,80]).grayscale()
    img.cache_dir = '/tmp/cache/'
    print img.render().filename     # cached file path

"""



import Image as _Image
from PIL import Image as _pImage
import md5
import UserList
import os

# available filters

filters = {}

""" register a custom filter """
def register_filter(key, filter):
    filters[key] = filter


class ImageFilters(UserList.UserList):

    def mkhash(self):
        result = md5.new()
        for filter, args, kwargs in self:
            result.update(filter.__name__)
            result.update(str(args))
            result.update(str(kwargs))

        return result.hexdigest()


""" Base image class """
class Image(object):


    def __init__(self,filename=None,quality=None):
        import settings
        self.load(filename)
        self.rendered_image = None
        self.filters = ImageFilters()
        self.quality = quality or settings.JPEG_QUALITY

    def load(self,file):
        self.filename = file
        self.filters = ImageFilters()
        return self

    def __getattr__(self, attr):
        def callable(*args, **kwargs):
            if filters.has_key(attr):
                return self.process(filters[attr], *args, **kwargs)
            raise AttributeError("Unknown filter %s." % attr)
        return callable

    def process(self, filter_instance, *args, **kwargs):
        self.rendered_image = None
        self.filters.append( (filter_instance, args, kwargs) )
        return self

    def render(self):
        if not self.rendered_image:
            if not self.filename:
                raise 'Image file not selected'
            img = _pImage.open(self.filename)
            self.transparency = img.info.get('transparency', None)
            for filter_instance, args, kwargs in self.filters:
                result = filter_instance(img, *args, **kwargs)
                # some filters returns a copy of an image, so check it
                # and replace image resource
                if isinstance(result, _pImage.Image):
                    img.im = result.im
            self.rendered_image = img
        return self

    def save(self, outfile=None):

        if not self.rendered_image:
            self.render()

        if not outfile:
            outfile = self.filename

        self.filename = outfile 
        kwargs = {
                'format':self.rendered_image.format,
                }

        if self.transparency:
            kwargs['transparency']=self.transparency
        if self.rendered_image.format == 'JPEG':
            kwargs['quality'] = self.quality 

        self.rendered_image.save(outfile, **kwargs)
        return self

    def __str__(self):
        self.render()
        return self.rendered_image.tostring()


CACHE_DIR = '/tmp/'

""" cached image class """
class CachedImage(Image):

    def __init__(self, *args, **kwargs):
        super(CachedImage, self).__init__(*args, **kwargs)
        self.cache_dir = CACHE_DIR
        self.cached = False
        self.cache_file = None # output filename

    def save(self, outfile=None):
        autocache_file = self._get_cache_file()
        outfile = outfile or autocache_file
        self.cache_file = outfile
        if not self.rendered_image:
            self.render()
        if (self.cached and autocache_file != outfile) or not self.cached:
            return super(CachedImage, self).save(outfile=outfile)
        self.filename = self.cache_file
        return self

    def _get_cache_file(self):
        filename = str(md5.new(str(self.quality) + self.filename + str(os.path.getsize(self.filename)) + self.filters.mkhash() + self.filename).hexdigest())
        filename += os.path.splitext(self.filename)[1]
        return os.path.join(self.cache_dir, filename)

    def render(self):
        if not self.cache_file:
            """
            rendering cached image firstly checks for already generated image
            but if output filename is not set, render should fail
            """
            raise RuntimeError('Cache filename not set. Cannot render.')

        if os.path.exists(self.cache_file):
            self.cached = True
            self.rendered_image = _pImage.open(self.cache_file)
            return self

        self.cached = False
        return super(CachedImage,self).render()
