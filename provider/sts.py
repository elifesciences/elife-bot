from provider import utils


def get_client(settings):
    "get an STS client"
    return utils.create_aws_connection(
        "sts",
        {
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
        },
    )


def assume_role(client, role_arn, role_session_name):
    "using STS client assume a role"
    sts_response = client.assume_role(
        RoleArn=role_arn, RoleSessionName=role_session_name
    )
    return sts_response
