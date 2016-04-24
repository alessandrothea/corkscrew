import collections

import ROOT


#
# Utility functions
#

#---
class TH1AddDirSentry:
    def __init__(self, status=False):
        self.status = ROOT.TH1.AddDirectoryStatus()
        ROOT.TH1.AddDirectory(status)

    def __del__(self):
        ROOT.TH1.AddDirectory(self.status)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.__del__()
#---
class TH1Sumw2Sentry:
    def __init__(self,sumw2=True):
        self.status = ROOT.TH1.GetDefaultSumw2()
        ROOT.TH1.SetDefaultSumw2(sumw2)

    def __del__(self):
        ROOT.TH1.SetDefaultSumw2(self.status)

    def __enter__(self, type, value, tb):
        return self

    def __exit__(self):
        self.__del__()


def plotNuisBand(hNom, hUp, hDwn):
    '''
    '''
    import numpy as np
    
    if not all([hNom, hUp, hDwn]):
        raise RuntimeError('Stica')

    ax      = hNom.GetXaxis()
    nbins   = ax.GetNbins()
    xs      = np.array( [ ax.GetBinCenter(i) for i in xrange(1,nbins+1) ], np.float32)
    wu      = np.array( [ ax.GetBinUpEdge(i)-ax.GetBinCenter(i)  for i in xrange(1,nbins+1) ], np.float32)
    wd      = np.array( [ ax.GetBinCenter(i)-ax.GetBinLowEdge(i) for i in xrange(1,nbins+1) ], np.float32)

    # Extract arrays ov values and errors
    nmarray     = np.array( [ hNom.GetBinContent(i) for i in xrange(1,nbins+1) ], np.float32)
    dwerrs      = np.array( [ hUp.GetBinContent(i)-hNom.GetBinContent(i) for i in xrange(1,nbins+1) ], np.float32)
    uperrs      = np.array( [ hNom.GetBinContent(i)-hDwn.GetBinContent(i) for i in xrange(1,nbins+1) ], np.float32)

    lErrs = ROOT.TGraphAsymmErrors(len(xs),xs,nmarray,wd,wu,dwerrs,uperrs)   

    return lErrs

def getNorms(pdf, obs, norms = None ):
    '''helper function to exctact the normalisation factors'''

    out = norms if norms != None else collections.OrderedDict()

#     logging.debug('searching norms in class: %s' % pdf.__class__.__name__ )

    # RooSimultaneous: pdf that spans multiple bins
    if isinstance(pdf,ROOT.RooSimultaneous):
        cat = pdf.indexCat()
        idx = cat.getIndex()
        for i in xrange(cat.numBins('')):
            cat.setBin(i)
            pdfi = pdf.getPdf(cat.getLabel());
            if pdfi.__nonzero__(): getNorms(pdfi, obs, out);
        # restore the old index
        cat.setIndex(idx)
        #pass


    elif isinstance(pdf,ROOT.RooProdPdf):
        pdfs = ROOT.RooArgList(pdf.pdfList())
        for pdfi in roofiter(pdfs):
            if pdfi.dependsOn(obs): getNorms(pdfi,obs,out)

    elif isinstance(pdf,ROOT.RooAddPdf):
        coefs = ROOT.RooArgList(pdf.coefList())
        for c in roofiter(coefs):
            # out[c.GetName()] =  c.getVal(obs)
            out[c.GetName()] =  c

    return out

#---
def findPdfs(top, obs, components = None ):

    out = components if components != None else collections.OrderedDict()

    # This top is a RooSimultaneous: acts on multiple bins
    if isinstance(top,ROOT.RooSimultaneous):
        cat = top.indexCat()
        idx = cat.getIndex()
        for i in xrange(cat.numBins('')):
            cat.setBin(i)
            pdfi = top.getPdf(cat.getLabel());
            if pdfi.__nonzero__(): findPdfs(pdfi, obs, out);

    # This top is a RooProdPdf: product of multiple pdfs
    elif isinstance(top,ROOT.RooProdPdf):
        pdfs = ROOT.RooArgList(top.pdfList())
        for pdfi in roofiter(pdfs):
            if pdfi.dependsOn(obs): findPdfs(pdfi,obs,out)

    # This top is a RooAddPdf: this is what I'm looking for
    elif isinstance(top,ROOT.RooAddPdf):
        pdfs = top.pdfList()

        # Assume
        for p in roofiter(pdfs):
            out[p.GetName()] = p

    return out



#---
class roofiter:
    def __init__(self,collection):
        self._iter = collection.fwdIterator()

    def __iter__(self):
        return self

    def next(self):
        o = self._iter.next()
        if not o: raise StopIteration
        return o

#---
def toList(stdList):
    l = []
    while stdList.size() > 0:
        l.append(stdList.front())
        stdList.pop_front()

    return l