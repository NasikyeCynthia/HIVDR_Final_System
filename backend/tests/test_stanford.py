import io
import json
import unittest
from unittest.mock import patch

from app.core.errors import DomainError
from app.services.stanford_service import analyze, validate_scores, check_connection, LEVELS


class StanfordTests(unittest.TestCase):
    def test_connection_check_sends_only_version_query(self):
        payload={'data':{'currentVersion':{'text':'fixture','publishDate':'2026-01-01'}}}
        with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(payload).encode())) as request:
            result=check_connection()
        self.assertTrue(result['connected'])
        sent=json.loads(request.call_args.args[0].data)
        self.assertEqual(set(sent),{'query'})
        self.assertNotIn('mutations',sent['query'])
        self.assertEqual(result['version']['text'],'fixture')

    def test_connection_check_rejects_failure_or_invalid_version(self):
        for payload in [[],{}, {'data':{'currentVersion':None}}, {'errors':[{'message':'failed'}]}]:
            with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(payload).encode())),self.assertRaises(DomainError):
                check_connection()
        with patch('urllib.request.urlopen',side_effect=TimeoutError),self.assertRaises(DomainError):
            check_connection()

    def payload(self, score=0, level=1):
        return {'data': {'currentVersion': {'text': 'fixture', 'publishDate': '2026-01-01'},
            'mutationsAnalysis': {'validationResults': [], 'drugResistance': [
                {'gene': {'name': 'RT'}, 'drugScores': [
                    {'drug': {'displayAbbr': '3TC'}, 'score': score, 'level': level}]}]}}}

    def test_all_five_categories_and_boundaries(self):
        for score, level in [(-10,1),(0,1),(9,1),(10,2),(14,2),(15,3),(29,3),(30,4),(59,4),(60,5),(100,5)]:
            with self.subTest(score=score):
                p = self.payload(score, level)
                with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(p).encode())):
                    result = analyze('mutations', 'RT:M184V')
                item = result['analysis']['drugResistance'][0]['drugScores'][0]
                self.assertEqual(item['text'], LEVELS[level])
                self.assertEqual(result['analyzed_genes'], ['RT'])

    def test_missing_or_inconsistent_results_are_not_susceptible(self):
        for score, level in [(None,1),(0,None),(60,1),(0,6),(True,1),(float('nan'),1)]:
            with self.subTest(score=score, level=level), self.assertRaises(DomainError):
                validate_scores(self.payload(score, level)['data']['mutationsAnalysis'])
        with self.assertRaises(DomainError):
            validate_scores({'drugResistance': []})

    def test_no_mutations_and_patient_text_are_rejected_before_network(self):
        with patch('urllib.request.urlopen') as request:
            for text in ['', 'none', 'patient-name', 'RT:patient', 'M184V']:
                with self.subTest(text=text), self.assertRaises(DomainError):
                    analyze('mutations', text)
            request.assert_not_called()

    def test_normalizes_and_deduplicates_mutations(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(self.payload()).encode())) as request:
            result = analyze('mutations', 'rt:m184v,RT:M184V; IN:R263K')
        sent = json.loads(request.call_args.args[0].data)
        self.assertEqual(sent['variables']['mutations'], ['RT:M184V','IN:R263K'])
        self.assertEqual(result['submitted_mutations'], sent['variables']['mutations'])

    def test_multiple_fasta_records_rejected(self):
        with patch('urllib.request.urlopen') as request, self.assertRaises(DomainError):
            analyze('sequence', '>sample1\n'+'ACGT'*30+'\n>sample2\n'+'ACGT'*30)
        request.assert_not_called()

    def test_quality_failure_and_graphql_error(self):
        p = self.payload()
        p['data']['mutationsAnalysis']['validationResults'] = [{'level':'SEVERE_WARNING','message':'Quality problem'}]
        for payload in [p, {'errors':[{'message':'Invalid query'}]}, [], {'data':{}}]:
            with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(payload).encode())), self.assertRaises(DomainError):
                analyze('mutations', 'RT:M184V')

    def test_unknown_input_kind_rejected(self):
        with self.assertRaises(DomainError):
            analyze('invalid-kind', 'RT:M184V')
