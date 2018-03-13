import os

from sagemaker import fw_utils

from test.integ.conftest import SCRIPT_PATH
from test.integ.docker_utils import train, HostingContainer
from test.integ.utils import create_config_files, copy_resource, file_exists


def test_layers_prediction(docker_image, sagemaker_session, opt_ml, processor):
    resource_path = os.path.join(SCRIPT_PATH, '../resources/mnist')

    copy_resource(resource_path, opt_ml, 'code')
    copy_resource(resource_path, opt_ml, 'data', 'input/data')

    s3_source_archive = fw_utils.tar_and_upload_dir(session=sagemaker_session.boto_session,
                                                    bucket=sagemaker_session.default_bucket(),
                                                    s3_key_prefix='test_job',
                                                    script='mnist.py',
                                                    directory=os.path.join(resource_path, 'code'))

    create_config_files('mnist.py', s3_source_archive.s3_prefix, opt_ml,
                        dict(training_steps=1, evaluation_steps=1))
    os.makedirs(os.path.join(opt_ml, 'model'))

    train(docker_image, opt_ml, processor)

    assert file_exists(opt_ml, 'model/export/Servo'), 'model was not exported'
    assert file_exists(opt_ml, 'model/checkpoint'), 'checkpoint was not created'
    assert file_exists(opt_ml, 'output/success'), 'Success file was not created'
    assert not file_exists(opt_ml, 'output/failure'), 'Failure happened'

    with HostingContainer(image=docker_image, opt_ml=opt_ml,
                          script_name='mnist.py', processor=processor) as c:
        c.execute_pytest('test/integ/container_tests/layers_prediction.py')