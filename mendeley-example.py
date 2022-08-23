from flask import Flask, redirect, render_template, request, session
import yaml
from pprint import pprint;
import pandas as pd
import os

from mendeley import Mendeley
from mendeley.session import MendeleySession

import os
def cls():
    os.system('cls' if os.name=='nt' else 'clear')


with open('config.yml') as f:
    config = yaml.full_load(f)

REDIRECT_URI = 'http://127.0.0.1:5000/oauth'

app = Flask(__name__)
app.debug = True
app.secret_key = config['clientSecret']

print(config['clientId'])
print(config['clientSecret'])

mendeley = Mendeley(config['clientId'], config['clientSecret'], REDIRECT_URI)


@app.route('/')
def home():
    if 'token' in session:
        return redirect('/listDocuments')

    auth = mendeley.start_authorization_code_flow()
    session['state'] = auth.state

    print(session['state'])
    print(auth.get_login_url())

    return render_template('home.html', login_url=(auth.get_login_url()))


@app.route('/oauth')
def auth_return():
    print(session)
    auth = mendeley.start_authorization_code_flow(state=session['state'])
    mendeley_session = auth.authenticate(request.url)

    session.clear()
    session['token'] = mendeley_session.token

    return redirect('/listDocuments')


@app.route('/listDocuments')
def list_documents():
    if 'token' not in session:
        return redirect('/')

    cls()

    with open('config.yml') as f:
        config = yaml.full_load(f)

    g_id                 = config['groupId']
    filename_csv         = config['filename_csv']
    filename_csv_sorted  = config['filename_csv_sorted']
    filename_html        = config['filename_html']
    filename_redirect_html = config['filename_redirect_html']
    root_pwd             = os.getcwd()

    #pprint(g_id)

    mendeley_session = get_session_from_cookies()
    name = mendeley_session.profiles.me.display_name

    #group = mendeley_session.resources.groups.Groups.get(id ="14b799ef-84e5-305a-af6d-b841193f5787")
    groups = mendeley_session.groups


    p_size = 500
    group = groups.get(id=g_id)
    # pprint(group)
    ll = group.documents.list(page_size=p_size, view='bib', sort='created', order='asc')
    # pprint(ll)
    # pprint(ll.count)

    attributes = dir(ll)
    # pprint(attributes)

    docs = ll.items
    # pprint("---------------")
    # pprint(docs)


    # pprint(docs)
    #docs = mendeley_session.documents.list(page_size='10', view='client').items
    #docs = group.list(page_size='10', view='client').items

    authors = parseAuthors(docs)
    sours = parseSources(docs)
    links = parseLinks(docs)

    pprint("---------------")
    #pprint(authors)
    #pprint(sours)
    # pprint(links)
    count = len(docs)


    createCSV(docs=docs, auths=authors, sours=sours, links=links, count=count, filename_csv=filename_csv, filename_csv_sorted=filename_csv_sorted)
    # filename_csv_sorted = './templates/fer_library_csv_sorted.csv'
    df = pd.read_csv(filename_csv_sorted, sep='\t')
    ind_sorted = df.values[:,0]
    #pprint("------&&&&&&--------")
    #pprint(ind_sorted)

    # output
    createHTML(docs=docs, auths=authors, sours=sours, links=links, count=count, ordered_indexes=ind_sorted, filename_html=filename_html)
    # pprint(os.system('pwd'))
    path_filename_html = 'file:///' + root_pwd + '/' + filename_html
    path_filename_csv_sorted = 'file:///' + root_pwd + '/' + filename_csv_sorted

    pprint(path_filename_html)
    pprint(path_filename_csv_sorted)

    return render_template(filename_redirect_html, my_html_path=path_filename_html, my_csv_path=path_filename_csv_sorted)


@app.route('/document')
def get_document():
    if 'token' not in session:
        return redirect('/')

    mendeley_session = get_session_from_cookies()

    document_id = request.args.get('document_id')
    doc = mendeley_session.documents.get(document_id)

    return render_template('metadata.html', doc=doc)


@app.route('/metadataLookup')
def metadata_lookup():
    if 'token' not in session:
        return redirect('/')

    mendeley_session = get_session_from_cookies()

    doi = request.args.get('doi')
    doc = mendeley_session.catalog.by_identifier(doi=doi)

    return render_template('metadata.html', doc=doc)


@app.route('/download')
def download():
    if 'token' not in session:
        return redirect('/')

    mendeley_session = get_session_from_cookies()

    document_id = request.args.get('document_id')
    doc = mendeley_session.documents.get(document_id)
    doc_file = doc.files.list().items[0]

    return redirect(doc_file.download_url)


@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect('/')


def get_session_from_cookies():
    return MendeleySession(mendeley, session['token'])

def parseAuthors(documents):
    """Aqi."""
    au = []
    i = 0
    for doc in documents:
        flag = []
        tmp = ''
        # pprint(documents[i].title)
        for author in doc.authors:
            if(tmp): # if not the first one
                tmp = tmp + ', '
                flag = 1
            if (author.first_name):
                tmp = tmp + author.first_name[0] + '. '
            tmp = tmp + author.last_name

        if(flag): # more than 1 author we write AND instead of ,
            # strValue = "This is the last rain of Season and Jack is here."
            strToReplace   = ','
            replacementStr = ' and'
            # Reverse the substring that need to be replaced
            strToReplaceReversed   = strToReplace[::-1]
            # Reverse the ©replacement substring
            replacementStrReversed = replacementStr[::-1]
            # Replace last occurrences of substring 'is' in string with 'XX'
            tmp = tmp[::-1].replace(strToReplaceReversed, replacementStrReversed, 1)[::-1]

        au.append(tmp)
        tmp = ''
        i=i+1
    return au


def parseSources(documents):
    #pprint(documents)
    so = []
    for doc in documents:
        tmp = ''
        ty= doc.type
        # pprint(ty)
        if ty=="journal":
            if (doc.source):
                tmp = tmp + doc.source + '. '
            if (doc.volume):
                tmp = tmp + doc.volume
            if (doc.issue):
                tmp = tmp + '(' + doc.issue + ')'
            if (doc.pages):
                tmp = tmp + ', pp: ' + doc.pages
        elif ty=="conference_proceedings":
            if (doc.source):
                tmp = tmp + doc.source
            if (doc.pages):
                tmp = tmp + ', pp: ' + doc.pages
        elif ty=="report":
            if (doc.institution):
                tmp = tmp + doc.institution
                # falta NUMBER
            if (doc.pages):
                tmp = tmp + ', pp: ' + doc.pages
        elif ty=="book":
            if (doc.source):
                tmp = tmp + doc.source
            if (doc.editors):
                for ed in doc.editors:
                    # pprint(doc.editors)
                    # pprint(ed)
                    # pprint(ed.last_name)
                    # pprint(ed.first_name)
                    tmp = tmp + ', '
                    if (ed.first_name):
                        tmp = tmp + ed.first_name
                    if (ed.last_name):
                        tmp = tmp + ' ' + ed.last_name
                    tmp = tmp + '(Eds.)'
            if (doc.edition):
                tmp = tmp + ' (' + doc.edition + ' Edition)'
            if (doc.publisher):
                tmp = tmp + ' ' + doc.publisher
        elif ty=="book_section":
            if (doc.source):
                tmp = tmp + doc.source
            if (doc.chapter):
                tmp = tmp + '. ' + doc.chapter
            if (doc.editors):
                for ed in doc.editors:
                    tmp = tmp + ', '
                    if (ed.first_name):
                        tmp = tmp + ed.first_name
                    if (ed.last_name):
                        tmp = tmp + ' ' + ed.last_name
                    tmp = tmp + '(Eds.)'
            if (doc.publisher):
                tmp = tmp + ' ' + doc.publisher
        elif ty=="thesis":
            if (doc.institution):
                tmp = tmp + doc.institution
            if (doc.pages):
                tmp = tmp + '. pp: ' + doc.pages
        elif ty=="magazine_article":
            if (doc.source):
                tmp = tmp + doc.source
            if (doc.volume):
                tmp = tmp + ', ' + doc.volume
            if (doc.issue):
                tmp = tmp + '(' + doc.issue + ')'
            if (doc.pages):
                tmp = tmp + ', pp: ' + doc.pages
        else:
            if (doc.institution):
                tmp = tmp + doc.institution
            if (doc.pages):
                tmp = tmp + ', pp: ' + doc.pages


#        pprint(tmp)
        so.append(tmp)

# case "generic":
# case "statute":
#
#
#            case "working_paper":
#            case "patent":
#            case "newspaper_article":
#            case "television_broadcast":
#            case "encyclopedia_article":
#            case "case":
#            case "film":
#            case "bill":
#
#

    #pprint(so)
    return so


def parseLinks(documents):
    #pprint(documents)
    li = []
    for doc in documents:
        tmp = ''
        if (doc.websites):
            tmp = tmp + doc.websites[0]
        li.append(tmp)

    return li

def createHTML(docs, auths, sours, links, count, ordered_indexes, filename_html):
    style_IEEE = {
        "authors":  {"data": '{}',
            "format": {"bold": 0, "italic": 0, "underscore": 0}},
        "title":    {"data": '{}',
            "format": {"bold": 0, "italic": 1, "underscore": 0}},
        "source":   {"data": '{}',
            "format": {"bold": 0, "italic": 0, "underscore": 0}},
        "year":     {"data": '{}',
            "format": {"bold": 0, "italic": 0, "underscore": 0}},
    }



    sty = style_IEEE
    # template = './templates/fer_library_template.html'
    # filename_html = './templates/fer_library_html.html'
    # com = 'cp {} {}'.format(template, filename)
    # os.system(com)

    # pprint('Before with')

    # try:
    #     f = open(filename)
    #     s = f.readline()
    #     i = int(s.strip())
    # except OSError as err:
    #     print("OS error: {0}".format(err))
    # except ValueError:
    #     print("Could not convert data to an integer.")
    # except BaseException as err:
    #     print(f"Unexpected {err=}, {type(err)=}")
    #     raise
    #



    if(ordered_indexes.any()):
        rang= ordered_indexes
    else:
        rang = range(count)

    ind  = 1
    with open(filename_html, 'w') as f:
        # The header
        f.writelines('<!DOCTYPE html>\n')
        f.writelines('<html lang="en">\n')
        f.writelines('<head>\n')
        f.writelines('    <meta charset="utf-8">\n')
        f.writelines('    <title>Mendeley Python Example</title>\n')
        f.writelines('</head>\n')
        f.writelines('<body>\n')

        # The table with data
        f.writelines('<table>\n')
        for i in rang:
            # new entry
            f.writelines('<tr  VALIGN=TOP>\n')
            # add the <td>


            f.writelines('   <td>\n')
            # NUMBER
            str = '[{}] '.format(ind)
            ind = ind+1
            f.writelines(str)
            f.writelines('   <t/d>\n')

            f.writelines('   <td>\n')

            # authors
            str = sty["authors"]["data"]
            str = str.format(auths[i])
            str = '   ' + applyStyle(str, sty['authors']['format'])
            str = str + '. '
            # we create the string for the bib items
            f.writelines(str)


            # Title
            str = sty["title"]["data"]
            str = str.format(docs[i].title)
            # if link, we add it in the Title
            if (links[i]):
                str = '<a href=\"{}">{}<a>'.format(links[i], str)
            str = applyStyle(str, sty['title']['format'])
            f.writelines(str)


            # source
            if (sours[i]):
                str = '. ' + sty["source"]["data"]
                str = str.format(sours[i])
                str = applyStyle(str, sty['source']['format'])
                f.writelines(str)


            # year
            str = ', ' + sty["year"]["data"]
            str = str.format(docs[i].year)
            str = applyStyle(str, sty['year']['format'])
            str = str + '.\n'
            f.writelines(str)



            # close the <td>
            f.writelines('   </td>\n')
            # close the <tr>
            f.writelines('</tr>\n')
        # close the table
        f.writelines('</table>\n')
        # close the body
        f.writelines('</body>\n')
        # close the html
        f.writelines('</html>\n')

        return 0


def applyStyle(str, sty):

    fd = sty
    str2 = str
    if fd['bold']:
        str2 = '<b>' + str2 + '</b>'
    if fd['italic']:
        str2 = '<i>' + str2 + '</i>'
    if fd['underscore']:
        str2 = '<u>' + str2 + '</u>'



    return str2




def createCSV(docs, auths, sours, links, count, filename_csv, filename_csv_sorted, incl_lastname=1):

    # template = './templates/fer_library_template.html'
    # filename_csv  = './templates/fer_library_csv.csv'
    # filename_csv_sorted = './templates/fer_library_csv_sorted.csv'
    # com = 'cp {} {}'.format(template, filename)
    # os.system(com)

    # pprint('Before with')

    # try:
    #     f = open(filename)
    #     s = f.readline()
    #     i = int(s.strip())
    # except OSError as err:
    #     print("OS error: {0}".format(err))
    # except ValueError:
    #     print("Could not convert data to an integer.")
    # except BaseException as err:
    #     print(f"Unexpected {err=}, {type(err)=}")
    #     raise
    #

    with open(filename_csv, 'w') as f:
        # The header
        f.writelines('Authors\t')
        f.writelines('Title\t')
        f.writelines('Source\t')
        f.writelines('Year\t')
        f.writelines('Links\t')
        f.writelines('LastName\t')
        f.writelines('\n')



        for i in range(count):
            # 0 Authors
            #pprint(i)
            #pprint(docs[i].year)
            f.writelines(auths[i])
            f.writelines('\t')
            # 1 Title
            f.writelines(docs[i].title)
            f.writelines('\t')
            # 2 sources
            f.writelines(sours[i])
            f.writelines('\t')
            # 3 year
            str = '{}'.format(docs[i].year)
            f.writelines(str)
            f.writelines('\t')
            # 4 links
            f.writelines(links[i])
            f.writelines('\t')
            # 5 last_name
            f.writelines(docs[i].authors[0].last_name)
            f.writelines('\n')


    df = pd.read_csv(filename_csv, sep='\t')
    df2 = df.sort_values(['Year', 'LastName', 'Title'],  ascending=[0,1,1], inplace=False)
    df2.to_csv(filename_csv_sorted, columns= ['Year', 'LastName', 'Title'], sep='\t')





if __name__ == '__main__':
    app.run()
