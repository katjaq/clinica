# -*- coding: utf-8 -*-
"""
Created on Wed Mar 16 16:23:47 2016

@author: jacquemont
"""

def launch(subject, files_directory, working_directory, datasink_directory):
    
    import nipype.interfaces.io as nio
    import nipype.interfaces.utility as niu
    import nipype.pipeline.engine as pe
    import os.path as op
    import clinica.pipeline.preproc.DWI_corrections as predifcorrect

# Inputs existence checking

    inputs=[files_directory, working_directory, datasink_directory]     
        
    for input_file in inputs:
        if not op.exists(input_file):
            raise IOError('file {} does not exist'.format(input_file))

    subject_list = [subject]
    
    infosource = pe.Node(interface=niu.IdentityInterface(fields=['subject_id']), name="infosource")
    infosource.iterables = ('subject_id', subject_list)
    
    datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_id'], outfields=['dwi_image','bvectors_directions','bvalues','T1_image']), name='datasource')
    datasource.inputs.base_directory = files_directory
    datasource.inputs.template = '*'
    datasource.inputs.field_template = dict(dwi_image='%s/DWI.nii',
                                            bvalues='%s/b_values.txt',
                                            bvectors_directions='%s/b_vectors.txt',
                                            T1_image='%s/T1.nii')
    datasource.inputs.template_args = dict(dwi_image=[['subject_id']],
                                           bvalues=[['subject_id']],
                                           bvectors_directions=[['subject_id']],
                                           T1_image=[['subject_id']])
    datasource.inputs.sort_filelist = True
    
    inputnode = pe.Node(interface=niu.IdentityInterface(fields=["dwi_image", "bvectors_directions", "bvalues", 'T1_image']), name="inputnode")
    
    pre = predifcorrect.prepare_data(datasink_directory)
    
    hmc = predifcorrect.hmc_pipeline(datasink_directory)
    
    ecc = predifcorrect.ecc_pipeline(datasink_directory)

    epi = predifcorrect.epi_pipeline(datasink_directory)

    bias = predifcorrect.remove_bias(datasink_directory)
    
    aac = predifcorrect.apply_all_corrections(datasink_directory)
    
    datasink = pe.Node(nio.DataSink(), name='datasink_tracto')
    datasink.inputs.base_directory = op.join(datasink_directory, 'Outputs_for_Tractography/')
    
    wf = pe.Workflow(name='preprocess')
    wf.base_dir = working_directory
    
    wf.connect([(infosource, datasource, [('subject_id','subject_id')])])
    wf.connect([(datasource, inputnode, [('dwi_image','dwi_image'), ('bvalues','bvalues'), ('bvectors_directions','bvectors_directions'), ('T1_image','T1_image')])])
    wf.conncet([(inputnode, pre, [('dwi_image', 'inputnode.dwi_image'),
                                  ('bvalues', 'bvalues'),
                                  ('bvectors_directions', 'bvectors_directions')])])
    wf.connect([(pre, hmc,[('outputnode.dwi_b0_merge','inputnode.in_file'), ('outputnode.out_bvals','inputnode.in_bval'), ('outputnode.out_bvecs','inputnode.in_bvec')])])
    wf.connect([(pre, hmc, [('outputnode.mask_b0','inputnode.in_mask')])])
    wf.connect([(hmc, ecc, [('outputnode.out_xfms','inputnode.in_xfms'),('outputnode.out_file','inputnode.in_file')])])
    wf.connect([(pre, ecc, [('outputnodeout_bvals','inputnode.in_bval')])])
    wf.connect([(pre, ecc, [('outputnode.mask_b0','inputnode.in_mask')])])
    wf.connect([(ecc, epi, [('outputnode.out_file','inputnode.DWI')])])
    wf.connect([(inputnode, epi, [('T1_image','inputnode.T1')])])
    wf.connect([(hmc, epi, [('outputnode.out_bvec','inputnode.bvec')])])
    wf.connect([(pre, aac, [('outputnode.dwi_b0_merge', 'inputnode.in_dwi')])])
    wf.connect([(hmc, aac, [('outputnode.out_xfms', 'inputnode.in_hmc')])])
    wf.connect([(ecc, aac, [('outputnode.out_xfms', 'inputnode.in_ecc')])])
    wf.connect([(epi, aac, [('outputnode.out_warp', 'inputnode.in_epi')])])
    wf.connect([(inputnode, aac, [('T1_image','inputnode.T1')])])
    
    
    wf.connect([(aac, bias, [('outputnode.out_file','inputnode.in_file')])])
    
    wf.connect([(bias, datasink, [('outputnode.out_file','DWI_hmc_ecc_epi_bias_corrected')])])
    wf.connect([(epi, datasink, [('outputnode.out_bvec', 'out_bvecs')])])
    wf.connect([(pre, datasink, [('outputnodeout_bvals','out_bvals')])])
    wf.connect([(bias, datasink, [('outputnode.b0_mask','b0_mask')])])
    
    wf.run()
