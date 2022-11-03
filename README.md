
# Harumonia`s Alfred Workflows

## notion search

Use [notion v1 api](https://developers.notion.com/reference/post-search) to search you notion database.  

Before using this workflow, you need insure that attention points below have been satisfied.  

- Python3 installed. The reuqests package also required.

- Apply for a integration from [notion integrations](https://www.notion.so/my-integrations). And then add the integrations to your notion database.

![notion config](https://raw.githubusercontent.com/zxjlm/my-static-files/main/img/notion%20config.png)

![notion search preview](https://s2.loli.net/2022/11/03/wjLVGtizWkxZdJK.png)

## confluence search

Base on [skleinei`s alfred-confluence](https://github.com/skleinei/alfred-confluence), but update the way to use [PATs](https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html#UsingPersonalAccessTokens-CreatingPATsintheapplication).

Make sure before you use this workflow that confluence version is 7.9 and later.(In other words, you should insure that confluence api use bearer for user authentication.)

Besides, this script allow you to search from content by using `--content` or `-c` explicitly. More query granularity may be support in the future.
