import boto3
import json
import os
import requests
import pandas as pd
import warnings

# Ignore all pyhon warnings here oh

from pandas import json_normalize

warnings.filterwarnings('ignore')


bucket                      = 'wmwaredata'
fileName                    = 'releases.json'
s3                          = boto3.client('s3')
git_token                   = os.getenv('GIT_TOKEN')
git_headers                 = {'Authorization': f'token {git_token}'}


def lambda_handler(event, context):

    # Listing repos
    resn                = requests.get("https://api.github.com/users/k8-proxy/repos").json()
    ra                  = json_normalize(resn, max_level=1)
    ran                 = ra[['id','name', 'html_url']]
    df1                 = pd.DataFrame(ran)
    df1                 = df1.rename({'html_url':'repo_url'}, axis=1)
    repos               = []

    for element in resn:
      ids               = element['id']
      repos.append(ids)

    # Getting release data
    data                =   []
    for repo in repos:
      url               = f'https://api.github.com/repositories/{repo}/releases'
      res               = requests.get(url, headers=git_headers).json()
      data1             = json_normalize(res, max_level=1)
      temp_df           = pd.DataFrame(data1)
      data.append(data1 )
      df2               = pd.concat(data, ignore_index=True)

    df2                 = df2[['html_url','tag_name', 'published_at','body']]

    # Merging release and repo data
    df1['join']         = 1
    df2['join']         = 1
    df                  = df1.merge(df2, on='join').drop('join', axis=1)

    df2.drop('join', axis=1, inplace=True)

    # Finding a matching name in the url
    df['match']       = [x[0] in x[1] for x in zip(df['name'], df['html_url'])]
    df                = df.loc[df['match'] == True]

    # Polishing results
    df.reset_index(drop=True, inplace=True)
    df                = df[['name','repo_url','body','tag_name', 'published_at']]
    df                = df.rename({'name':'repo_repo'}, axis=1)
    df                = df.rename({'body':'release_name'}, axis=1)
    df                = df.rename({'tag_name':'release_tag'}, axis=1)
    df                = df.rename({'published_at':'release_date'}, axis=1)

    # Creating a JSON file

    df = df.to_dict(orient ='records')

    uploads   = bytes(json.dumps(df, indent=4, sort_keys=True, default=str).encode('UTF-8'))

    # Uploading JSON file to s3 bucket
    s3.put_object(Bucket=bucket, Key=fileName, Body=uploads)

    message = {
      'message': 'JSON file succesfully created and uploaded to S3.'
       }

    return {
       'statusCode': 200,
       'headers': {'event-Type': 'application/json'},
       'outcome': json.dumps(message)
       }
