package mturk;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.PrintStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;

import com.amazonaws.AmazonClientException;
import com.amazonaws.AmazonServiceException;
import com.amazonaws.auth.profile.ProfileCredentialsProvider;
import com.amazonaws.mturk.addon.HITDataCSVWriter;
import com.amazonaws.mturk.addon.HITDataOutput;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3Client;
import com.amazonaws.services.s3.S3ResponseMetadata;
import com.amazonaws.services.s3.model.GetObjectRequest;
import com.amazonaws.services.s3.model.ListObjectsRequest;
import com.amazonaws.services.s3.model.ObjectListing;
import com.amazonaws.services.s3.model.ObjectMetadata;
import com.amazonaws.services.s3.model.PutObjectRequest;
import com.amazonaws.services.s3.model.S3Object;
import com.amazonaws.services.s3.model.S3ObjectSummary;

public class hitFiles {

	private PrintStream printhtml;
	/*
	 * bucketName: path where all files all stored in s3. AWS Credentials :
	 * access tokens acquired from AWS
	 */
	private String bucketName = "";
	private String hitsbucketName = "";
	private static String mturkURL = "";
	private AmazonS3 s3client;

	public static void main(String[] args) {
		/*
		 * Sanbox URL: https://workersandbox.mturk.com/mturk/externalSubmit.
		 * MTurk URL: https://www.mturk.com/mturk/externalSubmit.
		 */
		if (args[0].equals("-live")) {
			mturkURL = "https://www.mturk.com/mturk/externalSubmit";
		} else {
			mturkURL = "https://workersandbox.mturk.com/mturk/externalSubmit";
		}
		hitFiles hitFiles = new hitFiles(args[1]);
		deployHits deployHits = new deployHits(args[1]);
		
		hitFiles.getFolders(args[1]);
		if (deployHits.hasEnoughFund()) {
			deployHits.getFolders();
		}

	}

	hitFiles(String bucketName) {
		this.bucketName = "aisoftwareresearch/ner/" + bucketName;
		this.hitsbucketName = this.bucketName + "/hits";
		s3client = new AmazonS3Client(new ProfileCredentialsProvider());
	}

	/* Fetch all config JSONs inside the given s3 bucket */
	public void getFolders(String folderName) {
		String mainBucket = "aisoftwareresearch";
		String prefixKey = "ner/" + folderName + "/config";
		try {
			ListObjectsRequest listObjectsRequest = new ListObjectsRequest()
					.withBucketName(mainBucket).withPrefix(prefixKey);
			ObjectListing objectListing;
			do {
				objectListing = s3client.listObjects(listObjectsRequest);
				/*
				 * identify the sub folder names in the specified bucket. Store
				 * the sub folder names inside a separate array. This is done so
				 * that the files required for a particular hit aren't mixed up
				 * with data from another hit instance.
				 */
				for (S3ObjectSummary objectSummary : objectListing
						.getObjectSummaries()) {
					String key = objectSummary.getKey();

					if (!key.equalsIgnoreCase(prefixKey)) {
						key = key.substring((prefixKey + "/").length());
						if (key.indexOf(".json") > -1) {
							parseJSON(folderName, key);
						}
					}
				}
				listObjectsRequest.setMarker(objectListing.getNextMarker());
			} while (objectListing.isTruncated());

		} catch (Exception e) {
			System.err.println(e.getMessage());
		}
	}

	/*
	 * parse the json file in s3. create all components(html file, input file,
	 * properties file, question file) required to create a hit.
	 */
	public void parseJSON(String S3FolderName, String configName) {

		JSONParser parser = new JSONParser();
		String category = new String(), instructions, title;
		Map<String, String> sentences = new HashMap<String, String>();
		String filename = "";
		JSONArray scratch_categories;

		try {
			s3client.setEndpoint("s3-us-west-2.amazonaws.com");
			S3Object object = s3client.getObject(new GetObjectRequest(
					bucketName, "config/" + configName));
			InputStream objectData = object.getObjectContent();
			BufferedReader reader = new BufferedReader(new InputStreamReader(
					objectData));
			Object obj = parser.parse(reader);
			JSONArray array = (JSONArray) obj;
			for (Object o : array) {
				JSONObject jsonObject = (JSONObject) o;
				category = "";
				instructions = (String) jsonObject.get("instructions_html");
				title = (String) jsonObject.get("title");
				JSONArray categories = (JSONArray) jsonObject.get("categories");
				scratch_categories = (JSONArray) jsonObject
						.get("scratch_categories");
				Iterator<?> categoryIter = categories.iterator();
				while (categoryIter.hasNext()) {
					JSONObject innerObj = (JSONObject) categoryIter.next();
					category += innerObj.get("label") + ",";

				}
				/* remove last added comma from category */
				if (category.length() > 0
						&& category.charAt(category.length() - 1) == ',') {
					category = category.substring(0, category.length() - 1);
				}
				JSONArray sent = (JSONArray) jsonObject.get("hit_sentences");
				Iterator<?> sentIter = sent.iterator();
				while (sentIter.hasNext()) {
					JSONObject innerObj = (JSONObject) sentIter.next();
					sentences.put(innerObj.get("id").toString(),
							innerObj.get("sentence").toString());
				}

				filename = calculateSHA(jsonObject);
				createFolder(filename);
				generateHTML(title, instructions, category, sentences,
						filename, scratch_categories);
				createInputFile(sentences, filename);
				createPropertiesFile(jsonObject, filename, sentences);
				createQuestionFile(filename, S3FolderName);
				sentences.clear();

			}
			objectData.close();
		} catch (Exception e) {
			System.err.println("Parser" + e.getLocalizedMessage());
		}

	}

	/*
	 * Compute SHA for the contents of the JSON object. Input: JSON object
	 * output: SHA in hex format
	 */
	public String calculateSHA(JSONObject jsonObject) {
		String filename = "";
		try {
			MessageDigest digest = MessageDigest.getInstance("SHA-1");
			digest.reset();
			digest.update(jsonObject.toString().getBytes("UTF-8"));
			byte[] mdbytes = digest.digest();
			StringBuffer sb = new StringBuffer("");
			for (int i = 0; i < mdbytes.length; i++) {
				sb.append(Integer.toString((mdbytes[i] & 0xff) + 0x100, 16)
						.substring(1));
			}
			filename = sb.toString();

		} catch (Exception e) {
			System.err.println("SHA" + e.getLocalizedMessage());
		}
		return filename;
	}

	/*
	 * Creating a folder in S3. The folder will be created inside the Bucketname
	 * specified
	 */
	public void createFolder(String folderName) {
		ObjectMetadata metadata = new ObjectMetadata();
		metadata.setContentLength(0);
		/* Create empty content */
		InputStream emptyContent = new ByteArrayInputStream(new byte[0]);
		
		try {
			if (!hasHitsFolder(folderName)) {
				System.err.println("creating hits");
				PutObjectRequest putObjRequest = new PutObjectRequest(
						bucketName, "hits/", emptyContent, metadata);
				s3client.putObject(putObjRequest);
			}
			/* Create a PutObjectRequest passing the folder name suffixed by /. */
			PutObjectRequest putObjectRequest = new PutObjectRequest(
					hitsbucketName, folderName + "/", emptyContent, metadata);
			s3client.putObject(putObjectRequest);
		} catch (Exception e) {
			System.err.println(e.getMessage());
		}
	}
	/* check if S3 contains hits folder for this bucket*/
	public boolean hasHitsFolder(String folderName) {
		boolean hasHitsFolder = false;
		try {
			
			ListObjectsRequest listObjectsRequest = new ListObjectsRequest()
			.withBucketName("aisoftwareresearch").withPrefix("ner/" + folderName + "/hits");
			hasHitsFolder = true;
		} catch (Exception e) {
			System.err.println(e.getMessage());
		}
		return hasHitsFolder;
	}
	
	public void generateHTML(String title, String instructions,
			String categories, Map<String, String> sentences, String filename,
			JSONArray scratch_categories) {
		int linenum = 1;
		try {
			OutputStream htmlfile = new FileOutputStream(new File(
					"src/mturk/ner.html"));
			PrintStream printhtml = new PrintStream(htmlfile);

			String htmlheader = "<html><head>";
			htmlheader += " <meta charset=\"utf-8\"><meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\">   <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">";
			htmlheader += "<script src=\"https://ajax.googleapis.com/ajax/libs/jquery/1.11.2/jquery.min.js\"></script>";
			htmlheader += "<script src = \"https://s3-us-west-2.amazonaws.com/aisoftwareresearch/ner_html/ner.js\"> </script>";
			htmlheader += "<script src = \"https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js\"> </script>";
			htmlheader += " <link rel=\"stylesheet\" type=\"text/css\" href=\"https://s3-us-west-2.amazonaws.com/aisoftwareresearch/ner_html/bootstrap_assets.css\">";
			htmlheader += "<link rel=\"stylesheet\" type=\"text/css\" href=\"https://maxcdn.bootstrapcdn.com/bootstrap/3.3.2/css/bootstrap.min.css\">";
			htmlheader += "<link rel=\"stylesheet\" type=\"text/css\" href=\"https://s3-us-west-2.amazonaws.com/aisoftwareresearch/ner_html/ner.css\">";
			htmlheader += "</head><body categories= \"" + categories + "\">";
			htmlheader += "<div class=\"container\"><div class=\"\">";
			
			htmlheader += "<div class=\"page-header\">	<h1>" + title
					+ "</h1>	</div>";
			htmlheader += instructions;
			/*
			 * form submit URL should point to MTurk sandbox / MTurk URL. Sanbox
			 * URL: https://workersandbox.mturk.com/mturk/externalSubmit. MTurk
			 * URL: https://www.mturk.com/mturk/externalSubmit. Assignment Id as
			 * a hidden parameter to pass the hit id while submitting data.
			 */
			htmlheader += "<form id=\"mturk_form\" method=\"POST\" action=\""
					+ mturkURL
					+ "\"><input type=\"hidden\" id=\"assignmentId\" name=\"assignmentId\" value=\"\">";
			htmlheader += "<h2>Mark Up the Following Sentences</h2>";
			String htmlfooter = "<div class=\"btn_wrapper\">	<button name='submit' class=\"submitBtn btn btn-primary\"> Submit</button>	</div>";
			htmlfooter += "<div class=\"modal fade\" id=\"modal_box\">	<div class=\"modal-dialog\">	<div class=\"modal-content\">";
			htmlfooter += "<div class=\"modal-header alert alert-danger modal_title_custom\">	<button type=\"button\" class=\"close\" data-dismiss=\"modal\" aria-label=\"Close\">";
			htmlfooter += "<span aria-hidden=\"true\">&times;</span></button>	<h4 class=\"modal-title\">Please complete annotations</h4></div><div class=\"modal-body\" id=\"modal-body-text\">";
			htmlfooter += "</div>	";
			htmlfooter += "<div class=\"modal-footer\">	<button type=\"button\" class=\"btn btn-default\" data-dismiss=\"modal\">OK</button>";
			htmlfooter += "</div> </div> </div> </div>";
			htmlfooter += "</form> </div> </div></body></html>";

			printhtml.println(htmlheader);

			Iterator<?> sentIter = sentences.entrySet().iterator();
			while (sentIter.hasNext()) {
				@SuppressWarnings("rawtypes")
				Map.Entry pair = (Map.Entry) sentIter.next();

				printhtml.println(createPanel(linenum,
						pair.getKey().toString(), pair.getValue().toString(),
						categories, scratch_categories));
				linenum++;
			}
			printhtml.println(htmlfooter);
			printhtml.close();
			htmlfile.close();
			uploadFile(filename, "html");
		} catch (Exception e) {
			System.err.println("HTML " + e.getLocalizedMessage());
		}
	}

	/*
	 * creates a panel for each sentence. Input: linenum - to keep track of
	 * sentence number; sentence - the text content of sentence;
	 * scratch_categories: the check boxes shown at the bottom of each sentence
	 * panel. It usually contains "no entity present" Output: String containing
	 * HTML mark up for the panel
	 */
	public String createPanel(int linenum, String elasticSearchID, String sentence,
			String category, JSONArray scratch_categories) {

		String panelHTML = "<div class=\"panel panel-primary\" name=\"parent_container\">";
		panelHTML += "<div class=\"panel-heading\"><h1 class=\"panel-title\">Sentence "
				+ linenum + "</h1></div>";
		panelHTML += "<div class=\"panel-body\" id=\"container_" + linenum
				+ "\">	<div class=\"sentence\"  elastic-search-id= \""
				+ elasticSearchID + "\" id=\"sentence_" + linenum + "\"> " + sentence
				+ "</div> </div>";
		/* panel footer - shld list all the categories */
		String[] categories = category.split(",");
		/*
		 * create a dummy tag
		 * 
		 * panelHTML +=
		 * "<div class=\"row sample_tag\" data-toggle=\"tooltip\" data-placement=\"left\" title=\"Please select text first.\">"
		 * +
		 * "<div class=\"col-xs-1\"></div><div class=\"col-xs-2\"><span class=\"glyphicon glyphicon-triangle-right\"></span></div>"
		 * +
		 * "<div class=\"col-xs-1\"></div><div name=\"radio_container\" class=\"col-xs-7\"><div class=\"row\">"
		 * ; for (int i = 0; i < categories.length; i++) { panelHTML +=
		 * "<div class=\"col-xs-3\"><label class=\"radio-inline\"><input type=\"radio\" name=\"sample\" value=\"\" disabled>"
		 * + categories[i]+"</label></div>"; } panelHTML +=
		 * "</div></div><div class=\"col-xs-1\"><button class=\"deleteBtn glyphicon glyphicon-remove\" name=\"deleteTag\" disabled></button></div></div>"
		 * ;
		 */
		Iterator<?> categoryIter = scratch_categories.iterator();
		while (categoryIter.hasNext()) {
			JSONObject innerObj = (JSONObject) categoryIter.next();
			panelHTML += "<div class=\"checkbox custom_checkbox\"><label> <input type=\"checkbox\" name= \""+ elasticSearchID+"checkbox\" value=\" "+ elasticSearchID+ "\t" +"no annotations\">"
					+ innerObj.get("label") + "</label> </div>";
		}
		panelHTML += "<div class=\"panel-footer\">Markup occurences of";
		for (int i = 0; i < categories.length; i++) {
			panelHTML += " <span class=\"text-primary\">" + categories[i]
					+ "</span>,";
		}

		panelHTML += " </div> </div>";
		return panelHTML;
	}

	/*
	 * creates the .input file. This file contains the id of each sentence. The
	 * ids are separated by "/". Input : sentences - hash map containing id and
	 * text content for all sentences in current JSON Object; filename - SHA of
	 * JSON content. Used to uniquely identify data in each hit.
	 */
	public void createInputFile(Map<String, String> sentences, String filename) {

		int size = sentences.size();
		char separator = '\\';
		String[] annotations = new String[size];
		int linenum = 0;
		try {

			String inputFile = "src/mturk/ner.input";
			HITDataOutput inputEditor = new HITDataCSVWriter(inputFile,
					separator, false, false);
			@SuppressWarnings("rawtypes")
			Iterator sentIter = sentences.entrySet().iterator();
			while (sentIter.hasNext()) {
				@SuppressWarnings("rawtypes")
				Map.Entry pair = (Map.Entry) sentIter.next();
				annotations[linenum] = pair.getKey().toString();
				linenum++;
			}
			inputEditor.setFieldNames(annotations);
			inputEditor.setFieldNames(annotations);
			uploadFile(filename, "input");
		} catch (Exception e) {
			System.err.println("input file" + e.getLocalizedMessage());
		}
	}

	/*
	 * creates properties file. It contains all the specifications for a
	 * particular hit. Input: jsonObject - current JSON object; filename - SHA
	 * of JSON object; sentences - needed here to create annotations. The
	 * annotations should match values in input file.
	 */
	public void createPropertiesFile(JSONObject jsonObject, String filename,
			Map<String, String> sentences) {

		try {
			OutputStream propFile = new FileOutputStream(new File(
					"src/mturk/ner.properties"));
			PrintStream printhtml = new PrintStream(propFile);
			if (jsonObject.get("title").toString().length() > 0)
				printhtml
						.println("title:" + jsonObject.get("title").toString());
			if (jsonObject.get("description").toString().length() > 0)
				printhtml.println("description:"
						+ jsonObject.get("description").toString());
			if (jsonObject.get("keywords").toString().length() > 0)
				printhtml.println("keywords:"
						+ jsonObject.get("keywords").toString());
			if (jsonObject.get("reward").toString().length() > 0)
				printhtml.println("reward:"
						+ Float.valueOf(jsonObject.get("reward").toString()));
			if (jsonObject.get("num_assignments").toString().length() > 0)
				printhtml.println("assignments:"
						+ Integer.parseInt(jsonObject.get("num_assignments")
								.toString()));
			/*
			 * Permitted length of annotation is 255 chars. Since the
			 * conacatenation of sentence IDs exceeds that, not giving that
			 * attribute in properties file.
			 */

			/*
			 * String annotations = new String(); Iterator<?> sentIter =
			 * sentences.entrySet().iterator(); while (sentIter.hasNext()) {
			 * 
			 * @SuppressWarnings("rawtypes") Map.Entry pair = (Map.Entry)
			 * sentIter.next(); annotations += "${" + pair.getKey().toString() +
			 * "},"; }
			 * 
			 * // remove last added comma from annotation if
			 * (annotations.length() > 0 &&
			 * annotations.charAt(annotations.length() - 1) == ',') {
			 * annotations = annotations .substring(0, annotations.length() -
			 * 1); } if (annotations.length() > 0)
			 * printhtml.println("annotation:" + annotations);
			 */
			if (jsonObject.get("assignment_duration").toString().length() > 0)
				printhtml.println("assignmentduration:"
						+ Integer.parseInt(jsonObject
								.get("assignment_duration").toString()));
			if (jsonObject.get("hit_lifetime").toString().length() > 0)
				printhtml.println("hitlifetime:"
						+ Integer.parseInt(jsonObject.get("hit_lifetime")
								.toString()));
			if (jsonObject.get("autoapproval").toString().length() > 0)
				printhtml.println("autoapprovaldelay:"
						+ Integer.parseInt(jsonObject.get("autoapproval")
								.toString())); /* units - days */

			/*
			 * Qualifications to filter turkers who match our specifications.
			 * The input file may contain more than one qualification.
			 */
			JSONArray qualifications = (JSONArray) jsonObject
					.get("qualifications");
			int qualificationCount = 1;
			Iterator<?> qualIter = qualifications.iterator();
			while (qualIter.hasNext()) {

				JSONObject innerObj = (JSONObject) qualIter.next();

				if (innerObj.get("id").toString().length() > 0) {
					printhtml.println("qualification." + qualificationCount
							+ ":" + innerObj.get("id").toString());
					printhtml.println("qualification.comparator."
							+ qualificationCount + ":"
							+ innerObj.get("comparator").toString());
					printhtml
							.println("qualification.value."
									+ qualificationCount
									+ ":"
									+ Integer.parseInt(innerObj.get("value")
											.toString()));
					printhtml.println("qualification.private."
							+ qualificationCount
							+ ":"
							+ Boolean.getBoolean(innerObj.get("private")
									.toString()));
					qualificationCount++;
				}

			}
			printhtml.close();
			propFile.close();
			uploadFile(filename, "properties");
		} catch (Exception e) {
			System.err.println("Properties" + e.getLocalizedMessage());
		}
	}

	/*
	 * creates question file. The question file match a XML format pre defined
	 * by amazon. The ExternalURL tag should point to the HTML file that is
	 * hosted in S3.
	 */
	public void createQuestionFile(String filename, String S3FolderName) {
		try {
			OutputStream quesFile = new FileOutputStream(new File(
					"src/mturk/ner.question"));
			printhtml = new PrintStream(quesFile);
			printhtml.println("<?xml version=\"1.0\"?>");
			printhtml
					.println("<ExternalQuestion xmlns=\"http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd\">");
			printhtml
					.println("<ExternalURL>https://aisoftwareresearch.s3.amazonaws.com/ner/"
							+ S3FolderName
							+ "/"
							+ filename
							+ "/"
							+ filename
							+ ".html</ExternalURL>	");
			printhtml.println("<FrameHeight>600</FrameHeight>");
			printhtml.println("</ExternalQuestion>");
			uploadFile(filename, "question");
		} catch (Exception e) {
			System.err.println("Question" + e.getLocalizedMessage());
		}

	}

	/*
	 * upload file to S3. Each file is put inside a folder. Folder Name is SHA
	 * of JSON
	 */
	public void uploadFile(String filename, String fileType) {
		String keyName = filename + "/" + filename + "." + fileType;
		String uploadFileName = "src\\mturk\\ner." + fileType;
		try {
			File file = new File(uploadFileName);
			s3client.putObject(new PutObjectRequest(hitsbucketName, keyName, file));
			System.out.println("uploaded:: " + fileType);
		} catch (AmazonServiceException ase) {
			System.out.println("Error Message:    " + ase.getMessage());
		} catch (AmazonClientException ace) {
			System.out.println("Error Message: " + ace.getMessage());
		}
	}

}