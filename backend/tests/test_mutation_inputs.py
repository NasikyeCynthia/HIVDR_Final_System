import unittest
from app.services.mutation_inputs import suggested_mutations,analysis_input,validate_group_input

class MutationInputTests(unittest.TestCase):
    def test_original_dataset_columns_with_frequencies(self):
        raw={'PI':'L24I,L33F,M46I,I54V,V82A','INSTI':'E157Q(99.7%), E138K(100.0%)',
             'NRTI':'M184V(99.2%),K65R','NNRTI':'K103N(99.2%)'}
        self.assertEqual(set(suggested_mutations(raw).split()),
            {'PR:L24I','PR:L33F','PR:M46I','PR:I54V','PR:V82A','IN:E157Q','IN:E138K','RT:M184V','RT:K65R','RT:K103N'})

    def test_unqualified_combined_field_does_not_override_gene_evidence(self):
        self.assertEqual(analysis_input({'NRTI':'M184V','INSTI':'R263K'},'M184V, R263K'),'RT:M184V IN:R263K')
        self.assertEqual(analysis_input({'All Mutations Combined':'M184V'}),'')

    def test_saved_gene_qualified_episode_is_preserved(self):
        self.assertEqual(analysis_input({'NRTI':'M184V'},'RT:K65R'),'RT:K65R')

    def test_aliases_and_combined_qualified_input(self):
        raw={'NRTI Mutations':'m184v','INSTI Mutations':'r263k','All Mutations Combined':'PR:M46I RT:M184V'}
        self.assertEqual(set(suggested_mutations(raw).split()),{'RT:M184V','IN:R263K','PR:M46I'})

    def test_mutation_entry_validation(self):
        self.assertEqual(validate_group_input('e157q(99.7%), IN:E157Q; E138K(100.0%)','IN'),['IN:E157Q','IN:E138K'])
        self.assertEqual(validate_group_input('T69del, M184MV','RT'),['RT:T69DEL','RT:M184MV'])
        self.assertEqual(validate_group_input(', ,','RT'),[])
        for value in ['Patient 7','unknown','E157Q(not a percentage)','RT:M184V']:
            with self.subTest(value=value),self.assertRaises(ValueError):validate_group_input(value,'IN')
