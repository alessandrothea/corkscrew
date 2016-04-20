#!/bin/env python
#
import logging

import ROOT

import os.path

import collections

import corkutils

#
# CorkPdf
#
class CorkPdf(object):
    """docstring for CorkPdf"""
    def __init__(self):
        super(CorkPdf, self).__init__()
        self.pdf = None
        self.bin = None
        self.proc = None
        self.obs = []
        self.pars = []

    def __str__(self):
        return ('%s bin:%s proc:%s obs:%s, pars:%s' % (self.pdf.GetName(),self.bin,self.proc,self.obs,self.pars) )

    __repr__ = __str__

class CorkNorm(object):
    """docstring for CorkNorm"""
    def __init__(self):
        super(CorkNorm, self).__init__()
        self.kind = None
        self.bin = None
        self.proc = None
        self.norm = None
        self.components = None
        
        
#
# Corkscrew class
#

class CorkScrew(object):
    """docstring for CorkScrew"""

    _log = logging.getLogger('CorkScrew')
    _combineLoaded = False
    _sep = '_'

    @classmethod
    def _ensureCombine(cls):
        if cls._combineLoaded:
            return

        ROOT.gSystem.Load('libHiggsAnalysisCombinedLimit')
        cls._combineLoaded = True
        cls._log.debug('Loaded libHiggsAnalysisCombinedLimit')

    @property
    def processes(self):
        return self._processes
    
    @property
    def bins(self):
        return self._bins
    

    def __init__(self, wsFilePath):
        super(CorkScrew, self).__init__()

        self._wsFilePath = wsFilePath

        # Ensure that combine is loaded
        self._ensureCombine()

        # Ensure ensure that list iterator works
        # self._ensureListIter()


    def createIndexes(self):
        
        # import pdb
        # pdb.set_trace()
        wsFile = ROOT.TFile(self._wsFilePath)

        if ( not wsFile.IsOpen() ):
            raise IOError('Failed to open '+self._wsFilePath)

        ws = wsFile.Get('w')
        self._ws = ws

        data = corkutils.toList(ws.allData())

        print 'Found',len(data),'datasets'

        if len(data) == 0:
            raise RuntimeError('No datasets! What?!?')
        elif len(data) > 2:
            raise RuntimeError('Too many datasets! Don\;t know what to do')

        data_obs = ws.data('data_obs')
        self._data = data_obs

        print 'DataSet: ',data_obs.GetName()

        obs = [v.GetName() for v in  roofiter(data_obs.get(0)) ]

        model_s = ws.pdf('model_s')
        model_b = ws.pdf('model_b')


        lProcesses = set()
        lBins = set()

        pdf = model_s
        pdf_obs  = pdf.getObservables(data_obs)

        # Read 
        lNorms = getNorms(pdf,pdf_obs)
        cNorms = collections.OrderedDict()

        for lName,lNorm in lNorms.iteritems():
            # print name,lCoeff
            tk = lName.split(self._sep)

            # print '+++',lName, lNorm.GetName()
            # print lNorm
            # lNorm.getComponents().Print()

            # for p in roofiter(lNorm.getComponents()):
            #     print p, p == lNorm

            # Parse name and extract bin + process
            if tk[0:3] != ['n','exp','final']:
                raise SyntaxError('Error:',n,'doesn\'t start with n_exp_final')

            if not tk[3].startswith('bin'):
                raise SyntaxError('biiiiin')

            lProcIdx = tk.index('proc')

            lProc = self._sep.join(tk[lProcIdx+1:])
            lBin = self._sep.join(tk[3:lProcIdx])[3:]

            lProcesses.add(lProc)
            lBins.add(lBin)

            cNorm = CorkNorm()
            cNorm.bin = lBin
            cNorm.proc = lProc
            cNorm.norm = lNorm
            # Try with getParameters
            cNorm.components = [c.GetName() for c in roofiter(lNorm.getParameters(self._data)) if c.GetName() != lNorm.GetName()]


            # print lBin,'|',lProc,':',lNorm.getVal(pdf_obs),' c:',cNorm.components
            self._log.debug('%s | %s : %s c: %s',lBin,lProc,lNorm.getVal(pdf_obs),cNorm.components)

            cNorms[lName] = cNorm

        # Norms
        self._normIdx = cNorms
        # 
        self._bins = lBins
        self._processes = lProcesses

        lPdfCollection = findPdfs(pdf,pdf_obs)

        cPdfs = collections.OrderedDict()
        
        for lName,lPdf in lPdfCollection.iteritems():
            # print lName, lPdf

            tk = lName.split(self._sep)

            if not tk[0].startswith('shape'):
                raise SyntaxError('No shape? Aaargh!')

            if tk[-1] != 'morph':
                raise SyntaxError('No morph? Aaargh!')

            lSubName = self._sep.join(tk[1:-1])

            # print lSubName

            # Make this a function
            lBin = None
            for b in lBins:
                if not lSubName.startswith(b):
                    continue
                lBin = b
                break
            
            if lBin is None:
                raise RuntimeError('Couldn\'t find bin for lPdf '+lName)
            # func end
            
            lProc = lSubName[len(lBin)+1:]
            
            cPdf = CorkPdf()

            cPdf.kind = tk[0][5:]
            cPdf.pdf = lPdf
            cPdf.bin = lBin
            cPdf.proc = lProc
            cPdf.obs = [obs.GetName() for obs in roofiter(lPdf.getObservables(self._data))]
            cPdf.pars = [par.GetName() for par in roofiter(lPdf.getParameters(self._data))]

            self._log.debug('Name \'%s\'| pdf: %s kind: %s bin: %s proc: %s obs: %s pars: %s',
                lName, cPdf.pdf, cPdf.kind, cPdf.bin, cPdf.proc, cPdf.obs, cPdf.pars)

            cPdfs[lName] = cPdf



        # Pdf index
        self._pdfIdx = cPdfs 

    # def run(self):
        # import pdb
        # pdb.set_trace()
        # self.createIndexes()

    def findProcessShape(self, bin, proc):
        res = collections.OrderedDict(
            [(k,v) for k,v in self._pdfIdx.iteritems() if (v.bin == bin and v.proc == proc)]
            )
        if not res:
            raise RuntimeError('No shape found')
        elif len(res) != 1:
            raise RuntimeError('Found multiple shape matching criteria')

        return res.popitem()[1]


    def findProcessNorm(self, bin, proc):
        res = collections.OrderedDict(
            [(k,v) for k,v in self._normIdx.iteritems() if (v.bin == bin and v.proc == proc)]
            )

        if not res:
            raise RuntimeError('No normalisation found')
        elif len(res) != 1:
            raise RuntimeError('Found multiple normalisations matching criteria')

        return res.popitem()[1]


    def analyze(self, aBin, aProc, aNuisance, aLogY = False ):

        # Resolve pdf
        # Throws if not found
        # lPdf = self._pdfIdx.get(pdfName)

        lPdf = self.findProcessShape(aBin, aProc)

        lNorm = self.findProcessNorm(aBin, aProc)


        # Resolve the nuisance
        lNuis = self._ws.var(aNuisance)
        if not lNuis.__nonzero__():
            raise RuntimeError('Nuisance '+aNuisance+' not found.')

        # Ensure that the selected nuisance is a parameter to the PDF
        if lNuis.GetName() not in lPdf.pars and lNuis.GetName() not in lNorm.components:
            raise RuntimeError('Nuisance '+aNuisance+' does not influence %s:%s' % (aBin, aProc))

        lNuis.Print()

        obs = lPdf.pdf.getObservables(self._data)

        print lNorm.norm

        self._log.info('Normalization for %s, %s', lPdf.bin, lPdf.proc)

        c1 = ROOT.TCanvas()
        c1.SetLogy(aLogY)

        with TH1AddDirSentry():
            # Create nominal histogram
            h0 = lPdf.pdf.createHistogram(lPdf.obs[0])
            lScale = lNorm.norm.getVal(obs)

            print 'Norm nominal:',lScale
            # Scale it up
            h0.Scale(lScale)

            h0.SetLineColor(ROOT.kBlack)
            h0.SetTitle('%s:%s - %s' % (aBin,aProc,aNuisance))

            h0.Draw()

            # Set nuisance to +1 (Up)
            lNuis.setVal(1)

            # Create nominal histogram
            hUp = lPdf.pdf.createHistogram(lPdf.obs[0])
            lScale = lNorm.norm.getVal(obs)
            print 'Norm up:',lScale

            # Scale it up
            hUp.Scale(lScale)

            hUp.SetLineColor(ROOT.kBlue)

            hUp.Draw('same')

            # Set nuisance to -1 (Down)
            lNuis.setVal(-1)

            hDwn = lPdf.pdf.createHistogram(lPdf.obs[0])
            lScale = lNorm.norm.getVal(obs)
            print 'Norm down:',lScale

            hDwn.Scale(lScale)

            hDwn.SetLineColor(ROOT.kRed)

            hDwn.Draw('same')

        lFileName = '%s_%s_%s.pdf' % (aBin, aProc, aNuisance)
        c1.SaveAs(lFileName)

        # Scale it down
        lNuis.setVal(0)





if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)

    cs = CorkScrew('model.root')

    try:
        cs.createIndexes()
    except RuntimeError as e:
        cs._log.error(e)

    cs.analyze('semileptonic','TT','symjer')
    cs.analyze('semileptonic','TT','symjes')

    for p in cs.processes:
        try:
            cs.analyze('semileptonic',p,'btag', True)
        except RuntimeError as e:
            print e