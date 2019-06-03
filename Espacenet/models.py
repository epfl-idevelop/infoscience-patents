"""
    (c) All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE, Switzerland, VPSI, 2017
"""

from .patent_models import Patent, PCTPatent, PatentClassificationWithDefault


ESPACENET_JSON_DATA_SAVE_FOLDER = '/var/www/infoscience.epfl.ch/private/tmp/espacenet'

class EspacenetMixin(object):
    """ Add the Espacenet tools to fill patents data
    """
    def __init__(self, abstract_fr = '', abstract_en = '', exchange_document = None, publication_reference = None,
                 *args, **kwargs):
        """
        exchange_document may be used to get data
        """

        self.invention_title_en = ''
        self.invention_title_fr = ''

        if exchange_document:
            self.set_from_exchange_document(exchange_document)
        elif publication_reference:
            self.set_from_publication_reference(publication_reference)
            # add family_id if given
            if kwargs.get('family_id'):
                self.family_id = kwargs['family_id']
        else:
            if abstract_fr:
                self.abstract_fr = abstract_fr
            if abstract_en:
                self.abstract_en = abstract_en
        
    def set_from_publication_reference(self, publication_reference_data):
        document_id = publication_reference_data['document-id']
        
        if not isinstance(document_id, (list, tuple)):
            document_id = [document_id]
        
        for document in document_id:
            if document.get('@document-id-type') and document['@document-id-type'] == 'docdb':
                self.number = document.get('doc-number', {}).get('$')
                self.country = document.get('country', {}).get('$')
                self.kind = document.get('kind', {}).get('$')
                self.date = document.get('date', {}).get('$')
    
    def set_from_exchange_document(self, exchange_document):
        """ build the patent from an exchange document """
        ######
        # Abstract
        ######    
        
        self.number = exchange_document.get('@doc-number')
        self.country = exchange_document.get('@country')
        self.family_id = exchange_document.get('@family-id') # look like we don't have any family info
        self.kind = exchange_document.get('@kind')
            
        try:
            abstracts = exchange_document['abstract']

            if not isinstance(abstracts, (list, tuple)):
                # if we have only one value
                abstracts = [abstracts]
            
            for abstract_dict in abstracts:
                abstract_text = ''
                if isinstance(abstract_dict['p'], (list, tuple)):
                    #if we have an array, join with '\n'
                    abstract_text = []
                    for abstract_p in abstract_dict['p']:
                        abstract_text.append(abstract_p['$'])
                        
                    abstract_text = "\n".join(abstract_text)
                else: 
                    abstract_text = abstract_dict['p']['$']                    
                
                if abstract_dict['@lang'] == 'en':
                    self.abstract_en = abstract_text
                else:
                    self.abstract_en = ''
                if abstract_dict['@lang'] == 'fr':
                    self.abstract_fr = abstract_text
                else:
                    self.abstract_fr = ''
        except KeyError:
            self.abstract_fr = ''
            self.abstract_en = ''
        
        # time to parse bibliographic data
        patent_bibliographic = exchange_document['bibliographic-data']
        
        ######
        # Date
        ######
        # we may have multiple format, like epodoc or docdb
        # as soon as we have a date, take it, it should be the
        # same for all format
        patent_publication_reference = patent_bibliographic['publication-reference']
        patent_ids = patent_publication_reference['document-id']
        
        for patent_id in patent_ids:
            try:
                self.date = patent_id['date']['$']
            except KeyError:
                self.date = None
        
        ######
        # Application date
        ######
        # Also fetch the application date, useful for PCTs.
        patent_application_reference = patent_bibliographic.get('application-reference', {})
        app_ids = patent_application_reference.get('document-id', [])

        for app_id in app_ids:
            self.application_date = app_id.get('date', {}).get('$')
            if self.application_date:
                break
        else:
            self.application_date = None
        
        ######
        # Title
        ######
        try:
            invention_titles = patent_bibliographic['invention-title']
            
            if not isinstance(invention_titles, (list, tuple)):
                # if we have only one value
                invention_titles = [invention_titles]                
            
            for invention_title in invention_titles:
                try:
                    if invention_title['@lang'] == 'fr':
                        self.invention_title_fr = invention_title['$']
                    elif invention_title['@lang'] == 'en':
                        self.invention_title_en = invention_title['$']
                except KeyError:
                    pass
        except KeyError:
            pass

        ######
        # inventors
        ######            
        try:
            inventors = []
            inventors_exchange = patent_bibliographic['parties']['inventors']['inventor']

            for inventor_exchange in inventors_exchange:
                # keep only original format, at we don't want year and country inside name
                if '@data-format' in inventor_exchange and  inventor_exchange['@data-format'] == 'original':
                    #sequence are here to keep the right order
                    sequence = inventor_exchange['@sequence']
                    name = inventor_exchange['inventor-name']['name']['$']
                    inventors.append((sequence, name))
                    
            self.inventors = inventors
        except KeyError:
            self.inventors = []
        
        ######
        # applicants
        ######            
        try:
            applicants = []
            applicants_exchange = patent_bibliographic['parties']['applicants']['applicant']

            for applicant_exchange in applicants_exchange:
                # keep only original format, at we don't want year and country inside name
                if '@data-format' in applicant_exchange and  applicant_exchange['@data-format'] == 'original':
                    #sequence are here to keep the right order
                    sequence = applicant_exchange['@sequence']
                    name = applicant_exchange['applicant-name']['name']['$']
                    applicants.append((sequence, name))
                    
            self.applicants = applicants
        except KeyError:
            self.applicants = []
        ######
        # Patent classifications
        ######
        try:
            classifications = []
            
            patents_classifications = patent_bibliographic['patent-classifications']['patent-classification']
            
            if not isinstance(patents_classifications, (list, tuple)):
                # if we have only one value
                patents_classifications = [patents_classifications]
                
            for pat_class in patents_classifications:
                full_class = {}
                if '@sequence' in pat_class:
                    full_class['sequence'] = pat_class['@sequence']
                
                if 'class' in pat_class and '$' in pat_class['class']:
                    full_class['class_nr'] = pat_class['class']['$']
                    
                if 'classification-value' in pat_class and '$' in pat_class['classification-value']: 
                    full_class['classification_value'] = pat_class['classification-value']['$']
                
                if 'classification-scheme' in pat_class and '@scheme' in pat_class['classification-scheme']:            
                    full_class['classification_scheme'] = pat_class['classification-scheme']['@scheme']
                    
                if 'main-group' in pat_class and '$' in pat_class['main-group']:
                    full_class['main_group'] = pat_class['main-group']['$']
                    
                if 'section' in pat_class and '$' in pat_class['section']:                
                    full_class['section'] = pat_class['section']['$']
                    
                if 'subclass' in pat_class and '$' in pat_class['subclass']:
                    full_class['subclass'] = pat_class['subclass']['$']
                    
                if 'subgroup' in pat_class and '$' in pat_class['subgroup']:
                    full_class['subgroup'] = pat_class['subgroup']['$']
                
                pc = PatentClassificationWithDefault(**full_class)
                
                classifications.append(pc)
            
            self.classifications = classifications
        except KeyError:
            pass        
    
    def _cache_filepath(self):
        filename = self.country + self.number
        file_path = ESPACENET_JSON_DATA_SAVE_FOLDER + '/' + filename + '.json'
        return file_path
    
    def fetch(self):
        """ load data for a patent from HD if available """
        # instantiate self.patent_query_class defined in the concrete class
        patent_query = self.patent_query_class()
        
        return patent_query.fetch(self, file_path=self._cache_filepath())
    
    def fetch_families(self, use_file_hd=True):
        """ load data and all linked patents from HD or from Espacenet
            If use_file_hd, create a file for this family, so next
            query on it will be done on disk
         """
        from .query import EspacenetFamilyPatentQuery

        if use_file_hd:
            filename = "family_%s%s" % (self.country, self.number)
            file_path = ESPACENET_JSON_DATA_SAVE_FOLDER + '/' + filename + '.json'
            return EspacenetFamilyPatentQuery().fetch(self, file_path=file_path)
        else:
            return EspacenetFamilyPatentQuery().fetch(self)

class EspacenetPCT(EspacenetMixin, PCTPatent):
    def __init__(self, *args, **kwargs):
        EspacenetMixin.__init__(self, *args, **kwargs)
        PCTPatent.__init__(self, *args, **kwargs)
        
        from .query import EspacenetPCTPatentQuery
        self.patent_query_class = EspacenetPCTPatentQuery

class EspacenetPatent(EspacenetMixin, Patent):
    def __init__(self, *args, **kwargs):
        EspacenetMixin.__init__(self, *args, **kwargs)
        Patent.__init__(self, *args, **kwargs)
                
        from .query import EspacenetPatentQuery
        self.patent_query_class = EspacenetPatentQuery
