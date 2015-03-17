package mturk;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Date;
import java.util.Iterator;
import java.util.Properties;

import com.amazonaws.auth.profile.ProfileCredentialsProvider;
import com.amazonaws.mturk.addon.HITDataBuffer;
import com.amazonaws.mturk.addon.HITDataCSVWriter;
import com.amazonaws.mturk.addon.HITDataInput;
import com.amazonaws.mturk.addon.HITDataOutput;
import com.amazonaws.mturk.addon.HITProperties;
import com.amazonaws.mturk.addon.HITQuestion;
import com.amazonaws.mturk.requester.HIT;
import com.amazonaws.mturk.service.axis.RequesterService;
import com.amazonaws.mturk.util.PropertiesClientConfig;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3Client;
import com.amazonaws.services.s3.model.GetObjectRequest;
import com.amazonaws.services.s3.model.ListObjectsRequest;
import com.amazonaws.services.s3.model.ObjectListing;
import com.amazonaws.services.s3.model.S3Object;
import com.amazonaws.services.s3.model.S3ObjectSummary;

public class nerHit {

	// Defining the locations of the input files
	private RequesterService service;
	String inputFile = "", propertiesFile = "", questionFile = "";
	private String bucketName = "", prefixKey = "";
	private AmazonS3 s3client;

	public nerHit(String bucketName) {
		service = new RequesterService(new PropertiesClientConfig(
				"mturk.properties"));
		this.bucketName = "aisoftwareresearch/ner/" + bucketName;
		this.prefixKey = "ner/" + bucketName;
		s3client = new AmazonS3Client(new ProfileCredentialsProvider());
		s3client.setEndpoint("s3-us-west-2.amazonaws.com");
	}

	public boolean hasEnoughFund() {
		double balance = service.getAccountBalance();
		System.out.println("Got account balance: "
				+ RequesterService.formatCurrency(balance));
		return balance > 0;
	}

	public void getFolders() {
		ArrayList<String> folderNames = new ArrayList<String>();

		String mainBucket = "aisoftwareresearch";
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
					System.out.println(key);
					if (!key.equalsIgnoreCase(prefixKey)) {
						key = key.substring((prefixKey + "/").length());

						if (key.indexOf('/') > -1) {
							String[] keyParts = key.split("/");
							System.out.println(keyParts.length);
							if (keyParts.length == 1) {
								folderNames.add(keyParts[0]);
							}
						}
					}
				}
				listObjectsRequest.setMarker(objectListing.getNextMarker());
			} while (objectListing.isTruncated());

			Iterator<String> folderIter = folderNames.iterator();
			while (folderIter.hasNext()) {
				String currFileName = folderIter.next();
				System.out.println(currFileName);
				inputFile = currFileName + "/" + currFileName + ".input";
				questionFile = currFileName + "/" + currFileName + ".question";
				propertiesFile = currFileName + "/" + currFileName
						+ ".properties";
				createHIT(inputFile, questionFile, propertiesFile);
			}

		} catch (Exception e) {
			System.err.println("hereee" + e.getMessage());
		}
	}

	public void createHIT(String inputFile, String questionFile,
			String propertiesFile) {

		HITQuestion question = new HITQuestion();
		Properties prop_map = new Properties();

		String questionXML = "";
		String prop_char = "", prop_key = "", prop_value = "", content = "";

		try {
			HITDataBuffer input_buffer = new HITDataBuffer();
			S3Object in_object = s3client.getObject(new GetObjectRequest(
					bucketName, inputFile));
			InputStream in_objectData = in_object.getObjectContent();
			BufferedReader in_reader = new BufferedReader(
					new InputStreamReader(in_objectData));
			while ((content = in_reader.readLine()) != null) {
				input_buffer.writeLine(content.split("\\\\"));
			}
			HITDataInput input = input_buffer;
			in_object.close();
			in_objectData.close();
			in_reader.close();
			S3Object ques_object = s3client.getObject(new GetObjectRequest(
					bucketName, questionFile));
			InputStream ques_objectData = ques_object.getObjectContent();
			BufferedReader ques_reader = new BufferedReader(
					new InputStreamReader(ques_objectData));
			while ((content = ques_reader.readLine()) != null) {
				questionXML += content;
			}
			question.setQuestion(questionXML);
			ques_object.close();
			ques_objectData.close();
			ques_reader.close();
			S3Object prop_object = s3client.getObject(new GetObjectRequest(
					bucketName, propertiesFile));
			InputStream prop_objectData = prop_object.getObjectContent();
			BufferedReader prop_reader = new BufferedReader(
					new InputStreamReader(prop_objectData));
			while ((content = prop_reader.readLine()) != null) {
				prop_char = content;
				prop_key = prop_char.split(":")[0];
				prop_value = prop_char.split(":")[1];
				prop_map.setProperty(prop_key, prop_value);
			}
			HITProperties props = new HITProperties(prop_map);
			prop_object.close();
			prop_objectData.close();
			prop_reader.close();

			HIT[] hits = null;

			System.out.println("--[Loading HITs]----------");
			Date startTime = new Date();
			System.out.println("  Start time: " + startTime);
			HITDataOutput success = new HITDataCSVWriter(
					"src/mturk/success.success");
			HITDataOutput failure = new HITDataCSVWriter(
					"src/mturk/fail.failure");
			System.out.println("files done");
			hits = service.createHITs(input, props, question, success, failure);

			System.out.println("--[End Loading HITs]----------");
			Date endTime = new Date();
			System.out.println("  End time: " + endTime);
			System.out.println("--[Done Loading HITs]----------");
			System.out.println("  Total load time: "
					+ (endTime.getTime() - startTime.getTime()) / 1000
					+ " seconds.");

			if (hits == null) {
				throw new Exception("Could not create HITs");
			}

		} catch (Exception e) {
			System.err.println(e.getMessage());
		}
	}
}
