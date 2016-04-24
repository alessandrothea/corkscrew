#!/bin/env python
#
import argparse

import logging

import ROOT

import os.path

import collections

from corkutils import toList, roofiter, getNorms, findPdfs, TH1AddDirSentry, plotNuisBand

#
# CorkShape
#
class CorkShape(object):
    """docstring for CorkShape"""
    def __init__(self):
        super(CorkShape, self).__init__()
        self.pdf = None
        self.cat = None
        self.proc = None
        self.obs = []
        self.pars = []

    def __str__(self):
        return ('%s cat:%s proc:%s obs:%s, pars:%s' % (self.pdf.GetName(),self.cat,self.proc,self.obs,self.pars) )

    __repr__ = __str__

class CorkNormalization(object):
    """docstring for CorkNormalization"""
    def __init__(self):
        super(CorkNormalization, self).__init__()
        self.kind = None
        self.cat = None
        self.proc = None
        self.norm = None
        self.components = None
        
 
class CorkNuisHist(object):
    
    def __init__(self, hNom=None, hUp=None, hDwn=None, kind=None):
        self.hNom = hNom
        self.hUp = hUp
        self.hDwn = hDwn
        self.kind = kind

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
    def cats(self):
        return self._cats
    

    def __init__(self, wsFilePath):
        super(CorkScrew, self).__init__()

        self._wsFilePath = wsFilePath

        # Ensure that combine is loaded
        self._ensureCombine()

        self.createIndexes()


    def createIndexes(self):
        '''FIXME: Rewrite it making use of RooSimultaneous catergories


        cat = pdfTop.indexCat()
        idx = cat.getIndex()
        lAllCats = {}
        for i in xrange(cat.numBins('')):
            cat.setBin(i)

            lAllCats[cat.getLabel()] = i

        if aCat not in lAllCats:
            raise RuntimeError('Category '+aCat+' does not exist. '+', '.join(lAllCats))

        cat.setBin(lAllCats[aCat])

        lCatPdf = pdfTop.getPdf(aCat);
        lCatPdf.Print()

        lObs = lCatPdf.getObservables(self._data)
        print lObs
        lObsStrList = ','.join([ o.GetName() for o in roofiter(lObs) ])

        lScale = lCatPdf.expectedEvents(lObs)
        print 'Normalization: ', lScale

        h0 = lCatPdf.createHistogram(lObsStrList)


        '''
        
        wsFile = ROOT.TFile(self._wsFilePath)

        if ( not wsFile.IsOpen() ):
            raise FileNotFoundError('Failed to open '+self._wsFilePath)

        ws = wsFile.Get('w')
        self._ws = ws

        data = toList(ws.allData())

        print 'Found',len(data),'datasets'

        if len(data) == 0:
            raise RuntimeError('No datasets! What?!?')
        elif len(data) > 2:
            raise RuntimeError('Too many datasets! Don\;t know what to do!')

        data_obs = ws.data('data_obs')
        self._data = data_obs

        print 'DataSet: ',data_obs.GetName()

        obs = [v.GetName() for v in  roofiter(data_obs.get(0)) ]

        # Get the models
        self._modelS = ws.pdf('model_s')
        self._modelB = ws.pdf('model_b')

        # And store the 
        self._modelSPars = [ p.GetName() for p in roofiter(self._modelS.getParameters(data_obs)) if not p.isConstant() ]
        self._modelBPars = [ p.GetName() for p in roofiter(self._modelB.getParameters(data_obs)) if not p.isConstant() ]

        lProcesses = set()
        lCats = collections.defaultdict(list)
        # lProcessByCat = collections.defaultdict(list)

        model = self._modelS
        model_obs  = model.getObservables(data_obs)

        # Read 
        lNorms = getNorms(model,model_obs)
        lNormIndex = collections.OrderedDict()

        for lName,lNorm in lNorms.iteritems():
            # Tokenize the name
            tk = lName.split(self._sep)

            # Parse name and extract bin + process
            if tk[0:3] != ['n','exp','final']:
                raise SyntaxError('Error:',n,'doesn\'t start with n_exp_final')

            if not tk[3].startswith('bin'):
                raise SyntaxError('biiiiin')

            lProcIdx = tk.index('proc')

            lProc = self._sep.join(tk[lProcIdx+1:])
            lCat = self._sep.join(tk[3:lProcIdx])[3:]

            lProcesses.add(lProc)
            lCats[lCat].append(lProc)

            cNorm = CorkNormalization()
            cNorm.cat = lCat
            cNorm.proc = lProc
            cNorm.norm = lNorm
            # Try with getParameters
            cNorm.components = [c.GetName() for c in roofiter(lNorm.getParameters(self._data)) if c.GetName() != lNorm.GetName()]


            # print lCat,'|',lProc,':',lNorm.getVal(model_obs),' c:',cNorm.components
            # self._log.debug('%s | %s : %s c: %s',lCat,lProc,lNorm.getVal(model_obs),cNorm.components)
            self._log.debug('%s | %s : %s',lCat,lProc,lNorm.getVal(model_obs))

            lNormIndex[lName] = cNorm

        # Norms
        self._normIdx = lNormIndex
        # 
        self._cats = lCats
        self._processes = lProcesses

        lPdfCollection = findPdfs(model,model_obs)

        lPdfIndex = collections.OrderedDict()
        
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
            lCat = None
            for c,pros in lCats.iteritems():
                print [c+self._sep+p for p in pros]
                # Check if subname is a match t
                if not lSubName in [c+self._sep+p for p in pros]:
                    continue
                # if not lSubName.startswith(b):
                #     continue
                lCat = c
                break
            
            if lCat is None:
                raise RuntimeError('Couldn\'t find category for lPdf '+lName)
            # func end
            
            lProc = lSubName[len(lCat)+1:]
            
            cPdf = CorkShape()

            cPdf.kind = tk[0][5:]
            cPdf.pdf = lPdf
            cPdf.cat = lCat
            cPdf.proc = lProc
            cPdf.obs = [obs.GetName() for obs in roofiter(lPdf.getObservables(self._data))]
            cPdf.pars = [par.GetName() for par in roofiter(lPdf.getParameters(self._data))]

            # self._log.debug('Name \'%s\'| pdf: %s kind: %s bin: %s proc: %s obs: %s pars: %s',
            #     lName, cPdf.pdf, cPdf.kind, cPdf.cat, cPdf.proc, cPdf.obs, cPdf.pars)
            self._log.debug('Name \'%s\'| pdf: %s kind: %s bin: %s proc: %s',
                lName, cPdf.pdf, cPdf.kind, cPdf.cat, cPdf.proc)
            lPdfIndex[lName] = cPdf



        # Pdf index
        self._pdfIdx = lPdfIndex 

    def findProcessShape(self, aCat, aProc):
        res = collections.OrderedDict(
            [(k,v) for k,v in self._pdfIdx.iteritems() if (v.cat == aCat and v.proc == aProc)]
            )
        if not res:
            raise RuntimeError('No shape found for %s:%s' % (aCat,aProc))
        elif len(res) != 1:
            raise RuntimeError('Found multiple shape matching criteria')

        return res.popitem()[1]


    def findProcessNorm(self, aBin, aProc):
        res = collections.OrderedDict(
            [(k,v) for k,v in self._normIdx.iteritems() if (v.cat == aBin and v.proc == aProc)]
            )

        if not res:
            raise RuntimeError('No normalisation found')
        elif len(res) != 1:
            raise RuntimeError('Found multiple normalisations matching criteria')

        return res.popitem()[1]


    def plotVariations(self, aPdf, aNorm, aData, aPar):

        par0 = aPar.getVal()

        # Get pdf observables
        lObs = aPdf.getObservables(aData)

        lNuisHist = CorkNuisHist()
        lObsStrList = ','.join([ o.GetName() for o in roofiter(lObs) ])

        with TH1AddDirSentry():

            aPar.setVal(0)
            
            # Create nominal histogram
            h0 = aPdf.createHistogram(lObsStrList)
            lScale = aNorm.getVal(lObs)

            self._log.info('Norm nominal: %s', lScale)
            # Scale it up
            h0.Scale(lScale)

            h0.SetLineColor(ROOT.kBlack)

            lNuisHist.hNom = h0

            # Set nuisance to +1 (Up)
            aPar.setVal(1)

            # Create nominal histogram
            hUp = aPdf.createHistogram(lObsStrList)
            lScale = aNorm.getVal(lObs)
            # print 'Norm up:',lScale
            self._log.info('Norm Up: %s', lScale)

            # Scale it up
            hUp.Scale(lScale)

            hUp.SetLineColor(ROOT.kBlue)

            lNuisHist.hUp = hUp

            # Set nuisance to -1 (Down)
            aPar.setVal(-1)

            hDwn = aPdf.createHistogram(lObsStrList)
            lScale = aNorm.getVal(lObs)
            # print 'Norm down:',lScale
            self._log.info('Norm Down: %s', lScale)

            hDwn.Scale(lScale)

            hDwn.SetLineColor(ROOT.kRed)

            lNuisHist.hDwn = hDwn

        aPar.setVal(par0)

        return lNuisHist


    def analyzeProcess(self, aBin, aProc, aNuisance):

        # Resolve pdf
        # Throws if not found
        # lPdf = self._pdfIdx.get(pdfName)

        lShape = self.findProcessShape(aBin, aProc)

        lNorm = self.findProcessNorm(aBin, aProc)


        # Resolve the nuisance
        lNuis = self._ws.var(aNuisance)
        if not lNuis.__nonzero__():
            raise RuntimeError('Nuisance '+aNuisance+' not found.')

        # Ensure that the selected nuisance is a parameter to the PDF
        if lNuis.GetName() not in lShape.pars and lNuis.GetName() not in lNorm.components:
            raise RuntimeError('Nuisance '+aNuisance+' does not influence %s:%s' % (aBin, aProc))

        lNuis.Print()

        obs = lShape.pdf.getObservables(self._data)

        # print lNorm.norm

        self._log.info('Normalization for %s, %s', lShape.cat, lShape.proc)
 

        lNuisHist = self.plotVariations(lShape.pdf, lNorm.norm, self._data, lNuis)

        lNuisHist.kind  = lShape.kind

        return lNuisHist

    # ---
    def drawVariations(self, aBin, aProc, aNuisance, aLogY = False):

        lNuisHist = self.analyzeProcess(aBin, aProc, aNuisance);

        c1 = ROOT.TCanvas()
        c1.SetLogy(aLogY)

        lNuisHist.hNom.SetTitle('%s:%s - %s' % (aBin,aProc,aNuisance))

        lNuisHist.hNom.Draw()
        lNuisHist.hUp.Draw('same')
        lNuisHist.hDwn.Draw('same')


        lFileName = '%s_%s_%s.pdf' % (aBin, aProc, aNuisance)
        c1.SaveAs(lFileName)       

    # ---
    def analyzeModelsB(self, aCat, aNuisance):

        if aNuisance not in self._modelSPars:
            raise RuntimeError('Nuisance '+aNuisance+' not found.')

        pdfTop = self._modelB


        cat = pdfTop.indexCat()
        idx = cat.getIndex()
        lAllCats = {}
        for i in xrange(cat.numBins('')):
            cat.setBin(i)

            lAllCats[cat.getLabel()] = i

        if aCat not in lAllCats:
            raise RuntimeError('Category '+aCat+' does not exist. '+', '.join(lAllCats))

        cat.setBin(lAllCats[aCat])

        lCatPdf = pdfTop.getPdf(aCat);
        lCatPdf.Print()

        lObs = lCatPdf.getObservables(self._data)
        print lObs
        lObsStrList = ','.join([ o.GetName() for o in roofiter(lObs) ])

        lScale = lCatPdf.expectedEvents(lObs)
        print 'Normalization: ', lScale

        h0 = lCatPdf.createHistogram(lObsStrList)
        h0.Scale(lScale)

        c1 = ROOT.TCanvas()

        h0.Draw()
        lFileName = 'pippoB.pdf'

        c1.SaveAs(lFileName)

        cat.setIndex(idx)

    def analyzeModels(self, aCat, aNuisance):

        if aCat not in self.cats:
            raise RuntimeError('OOoops')

        lAllHists = collections.defaultdict(collections.OrderedDict)

        print self.cats[aCat]
        for lProcName in self.cats[aCat]:
            nuis = cs.analyzeProcess(aCat,lProcName,aNuisance)

            lAllHists[nuis.kind][lProcName] = nuis

        with TH1AddDirSentry():

            hBkg = ROOT.THStack('bkg','B only - %s' % aNuisance)
            hBkgUp = ROOT.THStack('bkgUp','B only - %s up' % aNuisance)
            hBkgDwn = ROOT.THStack('bkgDwn','B only - %s down' % aNuisance)

            hSigBkg = ROOT.THStack('sig_bkg', 'S+B - %s' % aNuisance)
            hSigBkgUp = ROOT.THStack('sig_bkgUp', 'S+B - %s up' % aNuisance)
            hSigBkgDwn = ROOT.THStack('sig_bkgDown', 'S+B - %s down' % aNuisance)


            def stackUp( aStack, aHist,aColor=None):
                hClone = aHist.Clone()
                if aColor is not None:
                    hClone.SetLineColor(aColor)

                aStack.Add(hClone)

            for lProcName, lHistNuis in lAllHists['Bkg'].iteritems():
                # Bkg nominal
                stackUp(hBkg, lHistNuis.hNom, ROOT.kBlue)
                stackUp(hBkgUp, lHistNuis.hUp, ROOT.kBlue)
                stackUp(hBkgDwn, lHistNuis.hDwn, ROOT.kBlue)


                stackUp(hSigBkg, lHistNuis.hNom, ROOT.kBlue)
                stackUp(hSigBkgUp, lHistNuis.hUp, ROOT.kBlue)
                stackUp(hSigBkgDwn, lHistNuis.hDwn, ROOT.kBlue)

            for lProcName, lHistNuis in lAllHists['Sig'].iteritems():
                stackUp(hSigBkg, lHistNuis.hNom, ROOT.kRed)
                stackUp(hSigBkgUp, lHistNuis.hUp, ROOT.kRed)
                stackUp(hSigBkgDwn, lHistNuis.hDwn, ROOT.kRed)



            c1 = ROOT.TCanvas()

            lSigBkgSum = hSigBkg.GetStack().Last().Clone()

            lSigBkgSum.Draw()
            lSigBkgSum.SetTitle('%s:S+B - %s' % (aCat, aNuisance) )
            lSigBkgVar = plotNuisBand(hSigBkg.GetStack().Last(), hSigBkgUp.GetStack().Last(), hSigBkgDwn.GetStack().Last())
            lSigBkgVar.SetFillStyle(3004)
            lSigBkgVar.SetFillColor(ROOT.kRed)
            lSigBkgVar.SetLineColor(ROOT.kRed)
            lSigBkgVar.Draw('5 same')

            lBkgSum = hBkg.GetStack().Last().Clone()
            lBkgSum.SetTitle('%s:B - %s'% (aCat, aNuisance) )
            lBkgSum.Draw('same')
            lBkgVar = plotNuisBand(hBkg.GetStack().Last(), hBkgUp.GetStack().Last(), hBkgDwn.GetStack().Last())
            lBkgVar.SetFillStyle(3005)
            lBkgVar.SetFillColor(ROOT.kBlue)
            lBkgVar.SetLineColor(ROOT.kBlue)
            lBkgVar.Draw('5 same')

            lFileName = '%s_%s.pdf' % (aCat, aNuisance)
            c1.SaveAs(lFileName)   


if __name__ == '__main__':

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter) # Why this formatter? Which other formatters are available ?
    parser.add_argument('file')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.DEBUG)
    # logging.basicConfig(level=logging.INFO)



    cs = CorkScrew(args.file)


    # try:
    #     cs.createIndexes()
    # except RuntimeError as e:
    #     cs._log.error(e)

    cs.drawVariations('semileptonic','TT','symjer')
    # cs.analyzeProcess('semileptonic','TT','symjes')

    # for p in cs.processes:
    #     try:
    #         cs.analyzeProcess('semileptonic',p,'btag', True)
    #     except RuntimeError as e:
    #         print e
    #         
    
    for c in cs.cats:
        cs.analyzeModels(c,'symjer')

    