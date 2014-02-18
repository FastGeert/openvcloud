[actor] @dbtype:mem,osis
	"""
	    Lists all the images. A image is a template which can be used to deploy machines.
	"""    

	method:list
	    """
	    List the availabe images, filtering can be based on the user which is doing the request
	    """
	    result:list of images for each image the id common name and description is listed.

    method:delete
        """
        Delete a image, you need to have Write access on the image
        """
        var:imageid int,, id of the image to delete
        result: bool

