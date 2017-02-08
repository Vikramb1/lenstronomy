__author__ = 'sibirrer'

import numpy as np
import astrofunc.util as util

import lenstronomy.util as lenstronomy_util

class Trash(object):

    def __init__(self, makeImage):
        self.makeImage = makeImage

    def findIterative(self, x_min, y_min, sourcePos_x, sourcePos_y, deltapix, num_iter, kwargs_else=None, **kwargs_lens):
        """
        find iterative solution to the demanded level of precision for the pre-selected regions given a lense model and source position

        :param mins: indices of local minimas found with def neighborSelect and def valueSelect
        :type mins: 1d numpy array
        :returns:  (n,3) numpy array with exact position, displacement and magnification [posAngel,delta,mag]
        :raises: AttributeError, KeyError
        """
        num_candidates = len(x_min)
        x_mins = np.zeros(num_candidates)
        y_mins = np.zeros(num_candidates)
        values = np.zeros(num_candidates)
        for i in range(len(x_min)):
            l=0
            x_mapped, y_mapped = self.makeImage.mapping_IS(x_min[i], y_min[i], kwargs_else, **kwargs_lens)
            delta = np.sqrt((x_mapped - sourcePos_x)**2+(y_mapped - sourcePos_y)**2)
            potential, alpha1, alpha2, kappa, gamma1, gamma2, mag = self.makeImage.get_lens_all(x_min[i], y_min[i], kwargs_else, **kwargs_lens)
            DistMatrix = np.array([[1-kappa+gamma1, gamma2], [gamma2, 1-kappa-gamma1]])
            det = 1./mag
            posAngel = np.array([x_min[i], y_min[i]])
            while(delta > deltapix/100000 and l<num_iter):
                deltaVec = np.array([x_mapped - sourcePos_x, y_mapped - sourcePos_y])
                posAngel = posAngel - DistMatrix.dot(deltaVec)/det
                x_mapped, y_mapped = self.makeImage.mapping_IS(posAngel[0], posAngel[1], kwargs_else, **kwargs_lens)
                delta = np.sqrt((x_mapped - sourcePos_x)**2+(y_mapped - sourcePos_y)**2)
                potential, alpha1, alpha2, kappa, gamma1, gamma2, mag = self.makeImage.get_lens_all(posAngel[0], posAngel[1], kwargs_else, **kwargs_lens)
                DistMatrix=np.array([[1-kappa+gamma1, gamma2], [gamma2, 1-kappa-gamma1]])
                det=1./mag
                l+=1
            x_mins[i] = posAngel[0]
            y_mins[i] = posAngel[1]
            values[i] = delta
        return x_mins, y_mins, values

    def findImage(self, sourcePos_x, sourcePos_y, deltapix, numPix, kwargs_else=None, **kwargs_lens):
        """
        finds image position and magnification given source position and lense model

        :param sourcePos: source position in units of angel
        :type sourcePos: numpy array (2)
        :param args: contains all the lense model parameters
        :type args: variable length depending on lense model
        :returns:  (exact) angular position of (multiple) images [[posAngel,delta,mag]] (in pixel image , including outside)
        :raises: AttributeError, KeyError
        """
        x_grid, y_grid = util.make_grid(numPix,deltapix)
        x_mapped, y_mapped = self.makeImage.mapping_IS(x_grid, y_grid, kwargs_else, **kwargs_lens)
        absmapped = util.displaceAbs(x_mapped, y_mapped, sourcePos_x, sourcePos_y)
        x_mins, y_mins, values = util.neighborSelect(absmapped, x_grid, y_grid)
        if x_mins == []:
            return None, None
        num_iter = 1000
        x_mins, y_mins, values = self.findIterative(x_mins, y_mins, sourcePos_x, sourcePos_y, deltapix, num_iter, kwargs_else, **kwargs_lens)
        x_mins, y_mins, values = lenstronomy_util.findOverlap(x_mins, y_mins, values, deltapix)
        x_mins, y_mins = lenstronomy_util.coordInImage(x_mins, y_mins, numPix, deltapix)
        if x_mins == []:
            return None, None
        return x_mins, y_mins

    def findBrightImage(self, sourcePos_x, sourcePos_y, deltapix, numPix, magThresh=1., numImage=4, kwargs_else=None, **kwargs_lens):
        """

        :param sourcePos_x:
        :param sourcePos_y:
        :param deltapix:
        :param numPix:
        :param magThresh: magnification threshold for images to be selected
        :param numImage: number of selected images (will select the highest magnified ones)
        :param kwargs_lens:
        :return:
        """
        x_mins, y_mins = self.findImage(sourcePos_x, sourcePos_y, deltapix, numPix, kwargs_else, **kwargs_lens)
        mag_list = []
        for i in range(len(x_mins)):
            potential, alpha1, alpha2, kappa, gamma1, gamma2, mag = self.makeImage.get_lens_all(x_mins[i], y_mins[i], kwargs_else, **kwargs_lens)
            mag_list.append(abs(mag))
        mag_list = np.array(mag_list)
        x_mins_sorted = util.selectBest(x_mins, mag_list, numImage)
        y_mins_sorted = util.selectBest(y_mins, mag_list, numImage)
        return x_mins_sorted, y_mins_sorted
