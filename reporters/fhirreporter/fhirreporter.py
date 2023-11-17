import uuid
import hashlib
import sqlite3
from oakvar import BaseReporter
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.observation import ObservationComponent
from fhir.resources.humanname import HumanName
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.fhirtypes import Uri, String, RangeType, MetaType , IdentifierType
from fhir.resources.quantity import Quantity
from fhir.resources.identifier import Identifier


class Reporter(BaseReporter):
    SO_dict = {
        "start_lost": "SO:0002012",
        "intron_variant": "SO:0001627",
        "frameshift_elongation": "SO:0001909",
        "missense_variant": "SO:0001583",
        "stop_lost": "SO:0001578",
        "frameshift_truncation": "SO:0001910",
        "lnc_RNA": "SO:0002127",
        "inframe_insertion": "SO:0001821",
        "5_prime_UTR_variant": "SO:0001623",
        "synonymous_variant": "SO:0001819",
        "splice_site_variant": "SO:0001629",
        "3_prime_UTR_variant": "SO:0001624",
        "2kb_upstream_variant": "SO:0001636",
        "2kb_downstream_variant": "SO:0002083",
        "stop_gained": "SO:0001587",
        "retained_intron": "SO:0002113",
        "inframe_deletion": "SO:0001822",
        "misc_RNA": "SO:0000673",
        "complex_substitution": "SO:1000005",
        "processed_transcript": "SO:0001503",
        "transcribed_unprocessed_pseudogene": "SO:0002107",
        "unprocessed_pseudogene": "SO:0001760",
        "miRNA": "SO:0000276",
        "processed_pseudogene": "SO:0000043",
        "snRNA": "SO:0000274",
        "transcribed_processed_pseudogene": "SO:0002109",
        "NMD_transcript_variant": "SO:0001621",
        "unconfirmed_transcript": "SO:0002139",
        "pseudogene": "SO:0000336",
        "transcribed_unitary_pseudogene": "SO:0002108",
        "NSD_transcript": "SO:0002130",
        "snoRNA": "SO:0000275",
        "scaRNA": "SO:0002095",
        "unitary_pseudogene": "O:0001759",
        "polymorphic_pseudogene": "SO:0001841",
        "rRNA": "SO:0000252",
        "IG_V_pseudogene": "SO:0002102",
        "ribozyme": "SO:0000374",
        "TR_V_gene": "SO:0002137",
        "TR_V_pseudogene": "SO:0002103",
        "TR_D_gene": "SO:0002135",
        "TR_J_gene": "SO:0002136",
        "TR_C_gene": "SO:0002134",
        "TR_J_pseudogene": "SO:0002104",
        "IG_C_gene": "SO:0002123",
        "IG_C_pseudogene": "SO:0002100",
        "IG_J_gene": "SO:0002125",
        "IG_J_pseudogene": "SO:0002101",
        "IG_D_gene": "SO:0002124",
        "IG_V_gene": "SO:0002126",
        "translated_processed_pseudogene": "SO:0002105",
        "scRNA": "SO:0000013",
        "vault_RNA": "SO:0000404",
        "translated_unprocessed_pseudogene": "SO:0002106",
        "Mt_tRNA": "SO:0002129",
        "Mt_rRNA": "SO:0002128",
        "start_retained_variant": "SO:0002019",
        "stop_retained_variant": "SO:0001567",
        "exon_loss_variant": "SO:0001572",
        "transcript_ablation": "SO:0001893",
        "pseudogene_rRNA": "SO:0002111",
        "sRNA": "SO:0002352",
    }

    Chrom_dict = {
        "chr1": "LA21254-0",
        "chr2": "LA21255-7",
        "chr3": "LA21256-5",
        "chr4": "LA21257-3",
        "chr5": "LA21258-1",
        "chr6": "LA21259-9",
        "chr7": "LA21260-7",
        "chr8": "LA21261-5",
        "chr9": "LA21262-3",
        "chr10": "LA21263-1",
        "chr11": "LA21264-9",
        "chr12": "LA21265-6",
        "chr13": "LA21266-4",
        "chr14": "LA21267-2",
        "chr15": "LA21268-0",
        "chr16": "LA21269-8",
        "chr17": "LA21270-6",
        "chr18": "LA21271-4",
        "chr19": "LA21272-2",
        "chr20": "LA21273-0",
        "chr21": "LA21274-8",
        "chr22": "LA21275-5",
        "chrX": "LA21276-3",
        "chrY": "LA21277-1",
    }

    # def __init__(self):
    #    #super().__init__()
    #    self.dict_entries = None
    #    self.dict_bundles = None
    #    self.dict_patient = None
    #    self.dict_nums = None
    #
    #    self.prefix = None
    #    self.wf = None

    def setup(self):
        self.levels_to_write = self.conf.get("pages", "variant")
        self.filenames = []
        self.counter = 0

        self.samples = []
        self.bundles = []

        # establish filename with fhir suffix
        self.prefix = self.savepath

        # get sample names
        conn = sqlite3.connect(self.dbpath)
        curs = conn.cursor()
        curs.execute("SELECT DISTINCT base__sample_id FROM 'sample' ")
        for sample in curs.fetchall():
            if sample[0].count(",") < 1:
                self.samples.append(sample[0])

        def create_dict(keys):
            unique_dict = {}
            for key in keys:
                if key not in unique_dict:
                    unique_dict[key] = []
            return unique_dict

        self.dict_entries = create_dict(self.samples)
        self.dict_bundles = create_dict(self.samples)
        self.dict_patient = create_dict(self.samples)
        self.dict_nums = create_dict(self.samples)

        # get number of rows
        curs = conn.cursor()
        curs.execute("SELECT COUNT(*) from variant")
        self.num_rows = curs.fetchone()[0]

        # get str for id generation
        curs = conn.cursor()
        curs.execute('select colval from info where colkey="input_paths"')
        # get input_path and split is so that only path is part of id.
        self.str_id = curs.fetchone()[0].split(" ", 1)[-1]

        curs = conn.cursor()
        curs.execute('select colval from info where colkey="annotators"')
        self.str_id += curs.fetchone()[0][1:-1]
        self.str_id = self.str_id[1:-1]
        self.str_id = self.str_id[-32:]

        curs = conn.cursor()
        curs.execute('select colval from info where colkey="mapper"')
        self.str_id += curs.fetchone()[0]
        # make this bundle UUID

        for sample in self.samples:
            # create sample id
            sample_name = f"{self.str_id} + {sample}"
            hex_sample = hashlib.md5(sample_name.encode("utf-8")).hexdigest()

            # create patient
            sample_2_patient = Patient()
            name = HumanName()
            name.use = "official"
            name.given = [sample]
            sample_2_patient.name = [name]
            patient_id = str(uuid.UUID(hex=hex_sample))
            # add to patient dict for reference in row observations
            subject = Reference(type="Patient")
            subject.resource_type = "Reference"
            subject.reference = f"urn:uuid:{patient_id}"
            self.dict_patient[sample] = subject

            patient_entry = BundleEntry(
                resource=sample_2_patient, fullUrl=f"urn:uuid:{patient_id}"
            )
            self.dict_entries[sample].append(patient_entry)

            # create sample bundle and and it to dictionary
            name = f"bundle + {sample} + self.str_id"
            hex_sample = hashlib.md5(name.encode("utf-8")).hexdigest()
            bundle = Bundle(
                type="collection",
                identifier=Identifier(value=str(uuid.UUID(hex=hex_sample))),
            )
            self.dict_bundles[sample] = bundle
            # self.dict_entries[sample].append(BundleEntry(resource=subject))

        # create CodingResource for row ObservationResources to Use
        self.fhir_system = Uri("http://loinc.org")

    def uuid_maker(self, val: str):
        hex_str = hashlib.md5(val.encode("utf-8")).hexdigest()
        return uuid.UUID(hex=hex_str)

    def should_write_level(self, level):
        if self.levels_to_write is None:
            return True
        elif level in self.levels_to_write:
            return True
        else:
            return False

    def end(self):
        if self.module_options.get("all_transcripts") == "true":
            for sample in self.samples:
                # fill in bundles with entries
                self.dict_bundles[sample].entry = self.dict_entries[sample]
                obs = self.dict_bundles[sample]
                filename = str(self.prefix) + f"__{sample}.all.fhir.json"
                self.wf = open(filename, "w", encoding="utf-8")
                json_str = obs.json(indent=2)
                self.wf.write(json_str)
                self.filenames.append(filename)
            self.wf.close()
        else:
            for sample in self.samples:
                filename = str(self.prefix) + f"__{sample}.primary.fhir.json"
                self.wf = open(filename, "w", encoding="utf-8")
                self.dict_entries[sample]
                self.dict_bundles[sample].entry = self.dict_entries[sample]
                obs = self.dict_bundles[sample]
                json_str = obs.json(indent=2)
                self.wf.write(json_str)
                self.filenames.append(filename)
            self.wf.close()

        return self.filenames

        # assign entries to correct bundles
        # self.bundle.entry = self.entries

        # create a json_str from FHIR BundleResource
        # for x in self.bundles:
        #    json_str = x.json(indent=2)
        #    self.wf.write(json_str)
        # return[str(self.savepath)]
        # json_str = self.bundles.json(indent=2)

        # write json_file
        # self.wf.write(json_str)

        # self.wf.close()
        # return [str(self.savepath)]

    def write_preface(self, level: str):
        if level not in self.levels_to_write:
            return

    def write_table_row(self, row):
        # get samples that have variant(row)
        sample_with_variants = row["tagsampler__samples"].split(",")

        for sample in sample_with_variants:
 
            # create codingType for row  Variant Observation
            coding = Coding()
            coding.system = Uri("http://loinc.org")
            coding.code = "69548-6"
            code = CodeableConcept()
            code.coding = [coding]
            # create CC for Laboratory
            cat_coding = Coding()
            cat_coding.system = Uri(
                "http://terminology.hl7.org/CodeSystem/observation-category"
            )
            cat_coding.code = "laboratory"
            cat_cc = CodeableConcept()
            cat_cc.coding = [cat_coding]

            variant_comps = []



            # Get Alleles from sqlite file
            ref = row["base__ref_base"]
            alt = row["base__alt_base"]

            # make component:ref-allele (UNIVERSAL COMPONENT)
            coding_ref = Coding()
            coding_ref.system = Uri("http://loinc.org")
            coding_ref.code = "69547-8"  # always code for reference allele
            coding_ref.display = "Ref nucleotide"
            code_ref = CodeableConcept()
            code_ref.coding = [coding_ref]
            comp_ref = ObservationComponent(code=code_ref)
            comp_ref.valueString = ref
            variant_comps.append(comp_ref)

            # make component:alt-allele (UNIVERSAL COMPONENT)
            coding_alt = Coding()
            coding_alt.system = Uri("http://loinc.org")
            coding_alt.code = "69551-0"
            coding_alt.display = "Alt allele"
            code_alt = CodeableConcept()
            code_alt.coding = [coding_alt]
            comp_alt = ObservationComponent(code=code_alt)
            comp_alt.valueString = alt
            variant_comps.append(comp_alt)

            # get chrom and pos information
            chrom_number = row["base__chrom"]
            pos = row["base__pos"]

            # Make component:chromosome-identifier (UNIVERSAL COMPONENT)
            coding_chrom = Coding()
            coding_chrom.system = Uri("http://loinc.org")
            coding_chrom.code = "48000-4"
            code_chrom = CodeableConcept()
            code_chrom.coding = [coding_chrom]
            comp_chrom = ObservationComponent(code=code_chrom)

            comp_chrom.valueCodeableConcept = CodeableConcept(
                coding=[
                    Coding(
                        system=Uri("http://loinc.org"),
                        code=self.Chrom_dict[chrom_number],
                        display=f"Chromosome {chrom_number.strip('chr')}",
                    )
                ]
            )
            variant_comps.append(comp_chrom)

            # Make component:coordinate-system (UNIVERSAL COMPONENT)
            coding_counting = Coding()
            coding_counting.system = Uri("http://loinc.org")
            coding_counting.code = "92822-6"
            code_counting = CodeableConcept()
            code_counting.coding = [coding_counting]
            comp_counting = ObservationComponent(code=code_counting)

            cc_counting = CodeableConcept(
                coding=[
                    (
                        Coding(
                            system=Uri("http://loinc.org"),
                            code="LA30102-0",
                            display=String("1-based character counting"),
                        )
                    )
                ]
            )
            comp_counting.valueCodeableConcept = cc_counting

            variant_comps.append(comp_counting)

            # Make component: exact start-end (UNIVERSAL COMPONENT)
            coding_st_sne = Coding()
            coding_st_sne.system = Uri("http://loinc.org")
            coding_st_sne.code = "81254-5"
            coding_st_sne.display = "Genomic allele start-end"
            st_sne_value_low = Quantity(value=pos)
            st_sne_value_high = Quantity(value=row["base__pos_end"])
            code_sne = CodeableConcept(coding=[coding_st_sne])
            comp_sne = ObservationComponent(code=code_sne)
            comp_sne.valueRange = RangeType(
                low=st_sne_value_low, high=st_sne_value_high
            )
            variant_comps.append(comp_sne)

            # create single observation for row
            obs_row = Observation(
                status="final",
                code=code,
                subject=self.dict_patient[sample],
                category=[cat_cc],
            )
            obs_row.component = variant_comps

            # obtain rows for ID maker
            conn = sqlite3.connect(self.dbpath)
            curs = conn.cursor()
            curs.execute("SELECT COUNT(*) from variant")
            self.num_rows = curs.fetchone()[0]

            # make ID for variant observation
            id_maker_v = (
                (self.str_id)
                + f"""{str(row['base__chrom']) 
                     + str(row['base__pos']) 
                     + str(row['base__ref_base']) 
                     + str(row['base__alt_base'])}"""
            )
            variant_id = self.uuid_maker(id_maker_v + self.str_id)
            variant_uri = Uri(f"urn:uuid:{variant_id}")

            # make ID for MC observation
            id_maker_mc = (
                (self.str_id)
                + f"""{str(row['base__chrom']) 
                     + str(row['base__pos']) 
                     + str(row['base__ref_base']) 
                     + str(row['base__alt_base'])
                     + "molecular consequence 1"}"""
            )

            mc_id = self.uuid_maker(id_maker_mc + self.str_id)
            mc_uri = Uri(f"urn:uuid:{mc_id}")

            obs_row.meta = MetaType()
            obs_row.meta.profile = [
                "http://hl7.org/fhir/uv/genomics-reporting/StructureDefinition/variant"
            ]

            # Start Molecular Consequence Creation

            mc_row = Observation(
                status="final",
                category=[
                    CodeableConcept(
                        coding=[
                            Coding(
                                system=Uri(
                                    "http://terminology.hl7.org/CodeSystem/observation-category"
                                ),
                                code="laboratory",
                            ),
                            Coding(
                                system=Uri(
                                    "http://terminology.hl7.org/CodeSystem/v2-0074"
                                ),
                                code="GE",
                            ),
                        ]
                    )
                ],
                subject=self.dict_patient[sample],
                code=CodeableConcept(
                    coding=[
                        Coding(
                            system=Uri(
                                "http://hl7.org/fhir/uv/genomics-reporting/CodeSystem/tbd-codes-cs"
                            ),
                            code="molecular-consequence",
                            display="Molecular Consequence",
                        )
                    ]
                ),
            )
            mc_row.derivedFrom = [Reference(type=Uri('variant'),identifier=Identifier(value=str(variant_id)))]

            gene_id = row["base__hugo"]
            if gene_id is not None:
                coding_id = Coding()
                coding_id.system = Uri("http://loinc.org")
                coding_id.code = "48018-6"
                coding_id.display = "Gene studied [ID]"
                code_gene_id = CodeableConcept(coding=[coding_id])
                comp_gene_id = ObservationComponent(code=code_gene_id)
                comp_gene_id.valueCodeableConcept = CodeableConcept(
                    coding=[
                        Coding(
                            system=Uri("https://www.genenames.org/geneId"), code=gene_id
                        )
                    ]
                )
                mc_row.component = [comp_gene_id]
            else:
                mc_row.component = []
            # get primary transcript ENSEMBL
            primary_transcript = row["base__transcript"]
            coding_primary_transcript = Coding()
            coding_primary_transcript.system = "http://loinc.org"
            coding_primary_transcript.code = "51958-7"
            coding_primary_transcript.display = "Transcript reference sequence [ID]"
            code_transcript = CodeableConcept(coding=[coding_primary_transcript])
            comp_primary_transcript = ObservationComponent(code=code_transcript)
            coding_pt_comp = Coding()
            coding_pt_comp.system = "http://www.ensembl.org"
            coding_pt_comp.code = primary_transcript
            coding_pt_comp.display = primary_transcript
            comp_primary_transcript.valueCodeableConcept = CodeableConcept(
                coding=[coding_pt_comp],
            )
            mc_row.component.append(comp_primary_transcript)

            coding_primary_rseqtranscript = Coding()
            coding_primary_rseqtranscript.system = "http://loinc.org"
            coding_primary_rseqtranscript.code = "51958-7"
            coding_primary_rseqtranscript.display = "Transcript reference sequence [ID]"
            code_rseqtranscript = CodeableConcept(
                coding=[coding_primary_rseqtranscript]
            )
            comp_primary_rseqtranscript = ObservationComponent(code=code_rseqtranscript)
            coding_pt_rseqcomp = Coding()
            coding_pt_rseqcomp.system = "http://www.ncbi.nlm.nih.gov/refseq"
            coding_pt_rseqcomp.code = row["base__refseq"]
            coding_pt_rseqcomp.display = row["base__refseq"]
            comp_primary_rseqtranscript.valueCodeableConcept = CodeableConcept(
                coding=[coding_pt_rseqcomp]
            )
            mc_row.component.append(comp_primary_rseqtranscript)

            SO = row["base__so"]
            if SO != " " and SO is not None or SO != "" and SO is not None:
                SO_coding = Coding()
                SO_coding.system = "http://hl7.org/fhir/uv/genomics-reporting/STU2/CodeSystem-tbd-codes-cs"
                SO_coding.code = "feature-consequence"
                code_SO = CodeableConcept(coding=[SO_coding])
                comp_SO = ObservationComponent(code=code_SO)

                comp_SO.valueCodeableConcept = CodeableConcept(
                    coding=[
                        Coding(
                            system="http://sequenceontology.org",
                            code=SO,
                            display=self.SO_dict[SO],
                        )
                    ]
                )
                mc_row.component.append(comp_SO)

            aa_change = row["base__achange"]
            c_change = row["base__cchange"]

            # Make Component for achange (change)
            if aa_change != "" and aa_change != " ":
                # Ensembl achange
                coding_change = Coding()
                coding_change.system = Uri("http://loinc.org")
                coding_change.code = "48005-3"
                coding_change.display = "Amino acid change (pHGVS)"
                code_achange = CodeableConcept(coding=[coding_change])
                comp_achange = ObservationComponent(code=code_achange)
                comp_achange.valueCodeableConcept = CodeableConcept(
                    coding=[
                        Coding(
                            system=Uri("http://www.ensembl.org"),
                            code=f"{primary_transcript}:{aa_change}",
                            display=f"{primary_transcript}:{aa_change}",
                        )
                    ]
                )
                mc_row.component.append(comp_achange)

                # RefSeq achange
                coding_change = Coding()
                coding_change.system = Uri("http://loinc.org")
                coding_change.code = "48005-3"
                coding_change.display = "Amino acid change (pHGVS)"
                code_rseqachange = CodeableConcept(coding=[coding_change])
                comp_rseqachange = ObservationComponent(code=code_rseqachange)
                comp_rseqachange.valueCodeableConcept = CodeableConcept(
                    coding=[
                        Coding(
                            system=Uri("http://varnomen.hgvs.org"),
                            code=f"{row['base__refseq']}:{aa_change}",
                            display=f"{row['base__refseq']}:{aa_change}",
                        )
                    ]
                )
                mc_row.component.append(comp_rseqachange)

            # Make Component for cchange (change)
            if c_change != "" and c_change != " ":
                coding_c_change = Coding()
                coding_c_change.system = Uri("http://loinc.org")
                coding_c_change.code = "48004-6"
                coding_c_change.display = "DNA change (c.HGVS)"
                code_c_change = CodeableConcept(coding=[coding_c_change])
                comp_c_change = ObservationComponent(code=code_c_change)
                comp_c_change.valueCodeableConcept = CodeableConcept(
                    coding=[
                        Coding(
                            system=Uri("http://varnomen.hgvs.org"),
                            code=f"{primary_transcript}:{c_change}",
                            display=f"{primary_transcript}:{c_change}",
                        )
                    ]
                )
                mc_row.component.append(comp_c_change)

                coding_rseqc_change = Coding()
                coding_rseqc_change.system = Uri("http://loinc.org")
                coding_rseqc_change.code = "48004-6"
                coding_rseqc_change.display = "DNA change (c.HGVS)"
                code_rseqc_change = CodeableConcept(coding=[coding_rseqc_change])
                comp_rseqc_change = ObservationComponent(code=code_rseqc_change)
                comp_rseqc_change.valueCodeableConcept = CodeableConcept(
                    coding=[
                        Coding(
                            system=Uri("http://varnomen.hgvs.org"),
                            code=f"{row['base__refseq']}:{c_change}",
                            display=f"{row['base__refseq']}:{c_change}",
                        )
                    ]
                )
            mc_row.component.append(comp_rseqc_change)

            # add primary variant + molecular consequence to bundle
            converted_variant = BundleEntry(resource=obs_row, fullUrl=variant_uri)
            self.dict_entries[sample].append(converted_variant)

            converted_molecular = BundleEntry(resource=mc_row, fullUrl=mc_uri)
            self.dict_entries[sample].append(converted_molecular)

            # begin all_transcript module optionloop
            if self.module_options.get("all_transcripts") == "true":
                skip = False
                mc_num = 1
                all_mappings = row["base__all_mappings"].split(";")

                for mapping in all_mappings:
                    mc_num += 1
                    mapping_comps = []

                    mapping_list = mapping.split(":")

                    if len(mapping_list) > 1:
                        uniprot_id = mapping_list[1].strip()
                        sequence_ontology = mapping_list[3].strip()
                        list_so = sequence_ontology.split(",")
                        amino_acid_change = mapping_list[4].strip()
                        chromosome_change = mapping_list[5].strip()
                        if list_so == 'unknown':
                            skip = True
                    if skip: continue 
                    mc_mapping = Observation(
                        status="final",
                        category=[
                            CodeableConcept(
                                coding=[
                                    Coding(
                                        system=Uri(
                                            "http://terminology.hl7.org/CodeSystem/observation-category"
                                        ),
                                        code="laboratory",
                                    ),
                                    Coding(
                                        system=Uri(
                                            "http://terminology.hl7.org/CodeSystem/v2-0074"
                                        ),
                                        code="GE",
                                    ),
                                ]
                            )
                        ],
                        subject=self.dict_patient[sample],
                        code=CodeableConcept(
                            coding=[
                                Coding(
                                    system=Uri(
                                        "http://hl7.org/fhir/uv/genomics-reporting/CodeSystem/tbd-codes-cs"
                                    ),
                                    code="molecular-consequence",
                                    display="Molecular Consequence",
                                )
                            ]
                        ),
                    )


                    transcript = mapping_list[0].strip()
                    id_maker = (
                        (self.str_id)
                        + f"""{str(row['base__chrom']) 
                             + str(row['base__pos']) 
                             + str(row['base__ref_base']) 
                             + str(row['base__alt_base'] + transcript)
                             + str(mc_num)}"""
                    )
                    mapping_id = self.uuid_maker(id_maker + self.str_id)
                    uri_maker = Uri(f"urn:uuid:{mapping_id}")

                    # Ensembl transcript component
                    if len(transcript) > 0:
                        coding_transcript = Coding()
                        coding_transcript.system = "http://loinc.org"
                        coding_transcript.code = "51958-7"
                        coding_transcript.display = "Transcript reference sequence [ID]"
                        code_transcript = CodeableConcept(coding=[coding_transcript])
                        comp_transcript = ObservationComponent(code=code_transcript)
                        coding_comp = Coding()
                        coding_comp.system = "http://www.ensembl.org"
                        coding_comp.code = transcript
                        comp_transcript.valueCodeableConcept = CodeableConcept(
                            coding=[coding_comp]
                        )
                        mapping_comps.append(comp_transcript)

                        coding_rseqtranscript = Coding()
                        coding_rseqtranscript.system = "http://loinc.org"
                        coding_rseqtranscript.code = "51958-7"
                        coding_rseqtranscript.display = (
                            "Transcript reference sequence [ID]"
                        )
                        code_rseqranscript = CodeableConcept(coding=[coding_transcript])
                        comp_rseqtranscript = ObservationComponent(code=code_transcript)
                        coding_comp = Coding()
                        coding_comp.system = "http://www.ncbi.nlm.nih.gov/refseq"
                        coding_comp.code = row["base__refseq"]
                        comp_rseqtranscript.valueCodeableConcept = CodeableConcept(
                            coding=[coding_comp]
                        )

                        mapping_comps.append(comp_rseqtranscript)


                        if uniprot_id != "" or uniprot_id != "":
                            coding_id = Coding()
                            coding_id.system = Uri("http://loinc.org")
                            coding_id.code = "48018-6"
                            coding_id.display = "Gene studied [ID]"
                            code_uni_prot = CodeableConcept(coding=[coding_id])
                            comp_uni_prot = ObservationComponent(code=code_uni_prot)
                            comp_uni_prot.valueCodeableConcept = CodeableConcept(
                                text=f"{uniprot_id}"
                            )

                        # create SO system for SO list
                        so_system_coding = Coding()
                        so_system_coding.system = "http://hl7.org/fhir/uv/genomics-reporting/STU2/CodeSystem-tbd-codes-cs"
                        so_system_coding.code = "feature-consequence"
                        code_system = CodeableConcept(coding=[so_system_coding])
                        comp_SO_all = ObservationComponent(code=code_system)

                        coding_list = []

                        for so in list_so:
                            if so != "unknown" and so != "" and so != " ":
                                so_coding = Coding()
                                so_coding.system = "http://sequenceontology.org"
                                so_coding.code = self.SO_dict[so]
                                so_coding.display = so
                                coding_list.append(so_coding)

                        comp_SO_all.valueCodeableConcept = CodeableConcept(
                            coding=coding_list
                        )

                        mapping_comps.append(comp_SO_all)

                        # make a_change component
                        if amino_acid_change != "" and amino_acid_change != " ":
                            # Ensemble a_change
                            coding_change = Coding()
                            coding_change.system = Uri("http://loinc.org")
                            coding_change.code = "48006-1"
                            coding_change.display = "Amino Acid Change [type]"
                            code_achange = CodeableConcept(coding=[coding_change])
                            comp_achange = ObservationComponent(code=code_achange)
                            comp_achange.valueCodeableConcept = CodeableConcept(
                                coding=[
                                    Coding(
                                        system=Uri("http://www.ensembl.org"),
                                        code=f"{transcript}:{amino_acid_change}",
                                        display=f"{transcript}:{amino_acid_change}",
                                    )
                                ]
                            )
                            mapping_comps.append(comp_achange)

                            coding_change = Coding()
                            coding_change.system = Uri("http://loinc.org")
                            coding_change.code = "48006-1"
                            coding_change.display = "Amino Acid Change [type]"
                            code_refachange = CodeableConcept(coding=[coding_change])
                            comp_refachange = ObservationComponent(code=code_refachange)
                            comp_refachange.valueCodeableConcept = CodeableConcept(
                                coding=[
                                    Coding(
                                        system=Uri("http://varnomen.hgvs.org"),
                                        code=f"{row['base__refseq']}:{amino_acid_change}",
                                        display=f"{row['base__refseq']}:{amino_acid_change}",
                                    )
                                ]
                            )
                            mapping_comps.append(comp_refachange)

                        if chromosome_change != "" and chromosome_change != " ":
                            # make c_change component (ENSEMBL)
                            coding_c_change = Coding()
                            coding_c_change.system = Uri("http://loinc.org")
                            coding_c_change.code = "48004-6"
                            coding_c_change.display = "DNA change (c.HGVS)"
                            code_c_change = CodeableConcept(coding=[coding_c_change])
                            comp_c_change = ObservationComponent(code=code_c_change)
                            comp_c_change.valueCodeableConcept = CodeableConcept(
                                coding=[
                                    Coding(
                                        system=Uri("http://www.ensembl.org"),
                                        code=f"{transcript}:{chromosome_change}",
                                        display=f"{transcript}:{chromosome_change}",
                                    )
                                ]
                            )
                            mapping_comps.append(comp_c_change)
                            #
                            ##make rc_change component (RefSeq)
                            coding_rc_change = Coding()
                            coding_rc_change.system = Uri("http://loinc.org")
                            coding_rc_change.code = "48004-6"
                            coding_rc_change.display = "DNA change (c.HGVS)"
                            code_rc_change = CodeableConcept(coding=[coding_rc_change])
                            comp_rc_change = ObservationComponent(code=code_rc_change)
                            comp_rc_change.valueCodeableConcept = CodeableConcept(
                                coding=[
                                    Coding(
                                        system=Uri("http://varnomen.hgvs.org"),
                                        code=f"{row['base__refseq']}:{chromosome_change}",
                                        display=f"{row['base__refseq']}:{chromosome_change}",
                                    )
                                ]
                            )
                            mapping_comps.append(comp_rc_change)
                        mc_mapping.component = mapping_comps
                        mc_mapping.derivedFrom = [Reference(type=Uri('variant'),identifier=Identifier(value=str(variant_id)))]
                        mapping_ent = BundleEntry(
                            resource=mc_mapping, fullUrl=uri_maker
                        )
                        self.dict_entries[sample].append(mapping_ent)
